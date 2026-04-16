"""
Bot Response Generator

Main pipeline for generating and injecting bot responses in meetings.
Integrates: Detection → RAG Context → LLM Generation → TTS → Voice Injection
"""

import time
import logging
import asyncio
from typing import Optional
from datetime import datetime

from app.models.bot_response import BotResponse
from app.services.bot_speaking_engine import get_bot_speaking_engine
from app.services.bot_speaking_rate_limiter import (
    can_respond_now,
    increment_response_count,
    set_last_response_time
)
from app.services.rag_service import rag_service
from app.services.tts_service import tts_service
from app.services.recall_service import recall_service
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


# Response style configurations
STYLE_CONFIGS = {
    'professional': {
        'max_words': 40,
        'prompt_modifier': "Respond professionally and formally in 1-2 sentences."
    },
    'casual': {
        'max_words': 35,
        'prompt_modifier': "Respond in a casual, friendly tone in 1-2 sentences."
    },
    'technical': {
        'max_words': 60,
        'prompt_modifier': "Provide a technical, detailed response in 2-3 sentences."
    },
    'brief': {
        'max_words': 15,
        'prompt_modifier': "Respond in one short sentence (max 15 words)."
    }
}


def format_response_with_style(response: str, style: str) -> str:
    """
    Format LLM response according to style preference.

    Args:
        response: Raw LLM response
        style: Response style (professional, casual, technical, brief)

    Returns:
        Formatted response text truncated to style limits
    """
    config = STYLE_CONFIGS.get(style, STYLE_CONFIGS['professional'])

    # Truncate if too long
    words = response.split()
    if len(words) > config['max_words']:
        response = ' '.join(words[:config['max_words']]) + "..."
        logger.debug(f"Truncated response to {config['max_words']} words")

    return response


async def save_bot_response(
    bot_id: str,
    meeting_id: int,
    trigger_text: str,
    response_text: str,
    response_style: str,
    success: bool,
    latency_ms: int,
    audio_url: Optional[str] = None
) -> Optional[BotResponse]:
    """
    Save bot response to database for history tracking.

    Args:
        bot_id: ID of the bot
        meeting_id: ID of the meeting
        trigger_text: What triggered the response
        response_text: What the bot said
        response_style: Style used for response
        success: Whether injection was successful
        latency_ms: Total response generation time
        audio_url: Optional path to audio file

    Returns:
        BotResponse object or None if save failed
    """
    try:
        db = AsyncSessionLocal()

        bot_response = BotResponse(
            bot_id=bot_id,
            meeting_id=meeting_id,
            trigger_text=trigger_text,
            response_text=response_text,
            response_style=response_style,
            audio_url=audio_url,
            timestamp=datetime.utcnow(),
            success=success,
            latency_ms=latency_ms
        )

        db.add(bot_response)
        await db.commit()
        await db.refresh(bot_response)

        logger.info(
            f"Bot response saved: id={bot_response.id}, "
            f"meeting={meeting_id}, success={success}"
        )

        await db.close()
        return bot_response

    except Exception as e:
        logger.error(f"Error saving bot response: {e}", exc_info=True)
        return None


async def check_and_respond_if_addressed(
    meeting_id: int,
    bot_id: str,
    user_id: int,
    chunk_text: str,
    chunk_speaker: str,
    bot_name: str,
    response_style: str,
    max_responses: int
):
    """
    Check if bot was directly addressed and generate response if needed.

    This is the main entry point called from the webhook handler.

    Args:
        meeting_id: ID of the meeting
        bot_id: ID of the bot
        user_id: ID of the user who owns the bot
        chunk_text: Transcript text
        chunk_speaker: Name of the speaker
        bot_name: Name of the bot
        response_style: Response style to use
        max_responses: Max responses allowed for this meeting
    """
    engine = get_bot_speaking_engine()

    # Step 1: Check if bot should respond (direct address check)
    should_respond, reason = engine.should_respond(chunk_text, chunk_speaker, bot_name)

    if not should_respond:
        # Don't log every rejection - too noisy
        return

    # ========== BOT NAME DETECTED! ==========
    print("\n" + "="*80)
    print("🎯 BOT NAME DETECTED IN TRANSCRIPT!")
    print("="*80)
    print(f"Meeting ID: {meeting_id}")
    print(f"Bot Name: {bot_name}")
    print(f"Speaker: {chunk_speaker}")
    print(f"Text: {chunk_text}")
    print("="*80 + "\n")

    logger.info(
        f"🎯 BOT ADDRESSED! meeting={meeting_id}, bot='{bot_name}', "
        f"speaker='{chunk_speaker}', text='{chunk_text[:80]}'"
    )

    # Step 2: Check rate limits
    can_respond, limit_reason = await can_respond_now(meeting_id, bot_id, max_responses)

    if not can_respond:
        print(f"⚠️ RATE LIMITED: {limit_reason}\n")
        logger.warning(
            f"⚠️ Bot rate limited: meeting={meeting_id}, reason='{limit_reason}'"
        )
        return

    # Step 3: Queue response generation as background task
    print(f"✅ STARTING RESPONSE GENERATION PIPELINE...\n")

    logger.info(
        f"✅ Starting bot response pipeline: meeting={meeting_id}, style={response_style}"
    )

    asyncio.create_task(
        generate_and_inject_response_task(
            meeting_id=meeting_id,
            bot_id=bot_id,
            user_id=user_id,
            trigger_text=chunk_text,
            speaker_name=chunk_speaker,
            bot_name=bot_name,
            response_style=response_style
        )
    )


async def generate_and_inject_response_task(
    meeting_id: int,
    bot_id: str,
    user_id: int,
    trigger_text: str,
    speaker_name: str,
    bot_name: str,
    response_style: str
):
    """
    Background task to generate and inject bot response.

    Pipeline:
    1. Extract query from trigger text
    2. Generate response with RAG + LLM
    3. Apply style formatting
    4. Synthesize speech with TTS
    5. Inject audio to meeting
    6. Log response in database
    7. Update rate limiters

    Args:
        meeting_id: ID of the meeting
        bot_id: ID of the bot
        user_id: ID of the user
        trigger_text: Full text that triggered response
        speaker_name: Name of the speaker
        bot_name: Name of the bot
        response_style: Response style to use
    """
    start_time = time.time()
    response_text = ""
    success = False

    try:
        print("="*80)
        print("🤖 BOT RESPONSE GENERATION PIPELINE")
        print("="*80)
        print(f"Step 1: Extracting query from trigger text...")

        # Step 1: Extract query (remove bot name from trigger)
        engine = get_bot_speaking_engine()
        query = engine.extract_query_from_address(trigger_text, bot_name)
        print(f"   Trigger: '{trigger_text}'")
        print(f"   Query: '{query}'")

        # Step 2: Generate response with RAG + LLM
        print(f"\nStep 2: Generating response with RAG + LLM...")
        response_result = await rag_service.process_user_query(
            user_id=str(user_id),
            message=query,
            user_name=speaker_name,
            bot_name=bot_name,
            max_tokens=100,
            use_cache=True,
            auto_store=False  # Don't store bot responses in RAG
        )

        response_text = response_result['response']
        print(f"   ✅ LLM Response: '{response_text}'")
        print(f"   Latency: {response_result['llm_latency_ms']:.0f}ms")
        print(f"   Cached: {response_result.get('cached', False)}")

        # Step 3: Apply response style formatting
        print(f"\nStep 3: Applying response style ({response_style})...")
        response_text = format_response_with_style(response_text, response_style)
        print(f"   ✅ Formatted: '{response_text}'")

        # Step 4: Synthesize speech (TTS)
        print(f"\nStep 4: Synthesizing speech with TTS...")
        audio_data = await tts_service.synthesize_async(user_id, response_text)

        if not audio_data:
            raise Exception("TTS synthesis failed - no audio data returned")

        print(f"   ✅ TTS Complete: {len(audio_data)} bytes")

        # Step 5: Inject to meeting
        print(f"\nStep 5: Injecting audio to meeting...")
        inject_result = await recall_service.inject_output_audio_mp3(bot_id, audio_data)

        success = inject_result.get('success', False)

        if success:
            print(f"   ✅ VOICE INJECTION SUCCESSFUL!")
            print(f"\n🎉 BOT WILL SPEAK: '{response_text}'")
        else:
            print(f"   ❌ VOICE INJECTION FAILED: {inject_result.get('message')}")

        latency_ms = int((time.time() - start_time) * 1000)

        # Step 6: Log response in database
        print(f"\nStep 6: Saving to database...")
        await save_bot_response(
            bot_id=bot_id,
            meeting_id=meeting_id,
            trigger_text=trigger_text,
            response_text=response_text,
            response_style=response_style,
            success=success,
            latency_ms=latency_ms,
            audio_url=None  # Could store MP3 if needed
        )
        print(f"   ✅ Saved to bot_responses table")

        # Step 7: Update rate limiters (only if successful)
        if success:
            await increment_response_count(meeting_id)
            await set_last_response_time(meeting_id)
            print(f"   ✅ Rate limiters updated")

        print(f"\n{'='*80}")
        print(f"🏁 PIPELINE COMPLETE - Total Time: {latency_ms}ms")
        print(f"{'='*80}\n")

        logger.info(
            f"✅ Bot response complete: meeting={meeting_id}, "
            f"success={success}, latency={latency_ms}ms, text='{response_text[:50]}'"
        )

    except Exception as e:
        print(f"\n❌ PIPELINE FAILED!")
        print(f"   Error: {str(e)}")
        print(f"{'='*80}\n")

        logger.error(
            f"❌ Bot response pipeline failed: meeting={meeting_id}, error={e}",
            exc_info=True
        )

        # Log failed attempt
        latency_ms = int((time.time() - start_time) * 1000)
        await save_bot_response(
            bot_id=bot_id,
            meeting_id=meeting_id,
            trigger_text=trigger_text,
            response_text=response_text or f"Error: {str(e)}",
            response_style=response_style,
            success=False,
            latency_ms=latency_ms
        )
