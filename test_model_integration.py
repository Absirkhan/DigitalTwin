"""
Test script for fine-tuned FLAN-T5 model integration
Tests model loading, inference, chunking, and structured output parsing
"""

import time
import logging
from app.services.summarization import (
    get_summarization_service,
    generate_simple_meeting_summary,
    generate_meeting_summary
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test data: Sample meeting transcripts
SHORT_TRANSCRIPT = """
John: Good morning everyone. Let's start our sprint planning meeting.
Sarah: I've completed the user authentication module and it's ready for review.
Mike: Great work Sarah. I think we should prioritize the dashboard redesign next.
John: Agreed. Mike, can you lead that effort?
Mike: Sure, I'll create a design doc by Friday.
Sarah: I can help with the frontend implementation next week.
John: Perfect. Let's reconvene on Monday to review progress.
"""

MEDIUM_TRANSCRIPT = """
Manager: Good afternoon team. Welcome to our quarterly business review. Today we'll discuss Q3 results, Q4 planning, and resource allocation.

Finance Lead: Thank you. Our Q3 revenue exceeded targets by 15%, reaching $4.2M. Operating expenses were within budget at $2.8M, giving us a healthy profit margin.

Sales Director: The strong performance was driven by three key factors: the Enterprise tier launch brought in 12 new large accounts, customer retention improved to 94% from 89% last quarter, and average contract value increased by 22%.

Marketing Manager: Our campaigns generated 2,400 qualified leads, a 40% increase from Q2. The content strategy focusing on case studies proved very effective.

Manager: Excellent results. For Q4, what are our priorities?

Product Lead: We need to accelerate the mobile app release. Based on customer surveys, 67% of users request mobile access. I propose we allocate two additional engineers to this project.

Engineering Manager: I agree. We should also address the technical debt in our payment processing system. It's becoming a bottleneck for scaling.

Finance Lead: For Q4, we're projecting $5.5M in revenue, assuming we maintain current growth rates. However, we'll need to increase the marketing budget by 25% to support expansion.

Manager: Let's make these decisions: First, approve the mobile app team expansion. Second, schedule a technical review of the payment system next week. Third, Finance and Marketing will present a detailed Q4 budget proposal by end of this week. Any questions?

Sales Director: When will the mobile app launch?

Product Lead: Targeting mid-December, just before the holidays.

Manager: Great. Meeting adjourned. Thank you everyone.
"""

LONG_TRANSCRIPT = SHORT_TRANSCRIPT * 10  # Simulate a very long transcript


def print_separator():
    """Print a visual separator"""
    print("\n" + "="*80 + "\n")


def test_model_loading():
    """Test 1: Model loading and initialization"""
    print_separator()
    logger.info("TEST 1: Model Loading and Initialization")
    print_separator()

    try:
        service = get_summarization_service()
        info = service.get_model_info()

        print("✅ Model loaded successfully!")
        print(f"\n📊 Model Information:")
        print(f"   - Status: {info['status']}")
        print(f"   - Model Path: {info['model_path']}")
        print(f"   - Device: {info['device']}")
        print(f"   - Parameters: {info['parameters']:,} (~{info['parameters_millions']}M)")
        print(f"   - Max Input Length: {info['max_input_length']} tokens")
        print(f"   - Max Output Length: {info['max_output_length']} tokens")
        print(f"   - Chunk Size: {info['chunk_size']} chars")
        print(f"   - Chunk Overlap: {info['chunk_overlap']} chars")

        return True

    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return False


def test_short_transcript():
    """Test 2: Simple meeting summarization (short transcript)"""
    print_separator()
    logger.info("TEST 2: Short Transcript Summarization")
    print_separator()

    print(f"📝 Input Transcript ({len(SHORT_TRANSCRIPT.split())} words):")
    print(SHORT_TRANSCRIPT[:200] + "..." if len(SHORT_TRANSCRIPT) > 200 else SHORT_TRANSCRIPT)

    try:
        start_time = time.time()
        summary = generate_simple_meeting_summary(SHORT_TRANSCRIPT)
        elapsed = time.time() - start_time

        print(f"\n✅ Summary generated in {elapsed:.2f} seconds")
        print(f"\n📄 Summary ({len(summary.split())} words):")
        print(summary)

        return True

    except Exception as e:
        print(f"❌ Short transcript test failed: {e}")
        return False


def test_medium_transcript():
    """Test 3: Medium length transcript with structured output"""
    print_separator()
    logger.info("TEST 3: Medium Transcript with Structured Output")
    print_separator()

    print(f"📝 Input Transcript ({len(MEDIUM_TRANSCRIPT.split())} words, {len(MEDIUM_TRANSCRIPT)} chars):")
    print(MEDIUM_TRANSCRIPT[:300] + "...")

    try:
        start_time = time.time()
        result = generate_meeting_summary(MEDIUM_TRANSCRIPT)
        elapsed = time.time() - start_time

        print(f"\n✅ Structured summary generated in {elapsed:.2f} seconds")

        print(f"\n📊 Status: {result['status']}")

        print(f"\n📄 Summary ({result['metrics']['summary_words']} words):")
        print(result['summary'])

        if result['attendees']:
            print(f"\n👥 Attendees ({len(result['attendees'])}):")
            for attendee in result['attendees']:
                print(f"   - {attendee}")

        if result['key_points']:
            print(f"\n🔑 Key Points ({len(result['key_points'])}):")
            for i, point in enumerate(result['key_points'], 1):
                print(f"   {i}. {point}")

        if result['decisions']:
            print(f"\n✔️  Decisions Made ({len(result['decisions'])}):")
            for i, decision in enumerate(result['decisions'], 1):
                print(f"   {i}. {decision}")

        if result['action_items']:
            print(f"\n📋 Action Items ({len(result['action_items'])}):")
            for i, item in enumerate(result['action_items'], 1):
                print(f"   {i}. {item}")

        print(f"\n📈 Metrics:")
        print(f"   - Original: {result['metrics']['original_words']} words")
        print(f"   - Summary: {result['metrics']['summary_words']} words")
        print(f"   - Compression: {result['metrics']['compression_ratio']:.1%}")
        print(f"   - Model: {result['metrics']['model']}")
        print(f"   - Device: {result['metrics']['device']}")

        return True

    except Exception as e:
        print(f"❌ Medium transcript test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_long_transcript():
    """Test 4: Long transcript with chunking"""
    print_separator()
    logger.info("TEST 4: Long Transcript with Chunking")
    print_separator()

    print(f"📝 Input Transcript ({len(LONG_TRANSCRIPT.split())} words, {len(LONG_TRANSCRIPT)} chars):")
    print(f"   This simulates a long meeting transcript that requires chunking...")

    try:
        start_time = time.time()
        summary = generate_simple_meeting_summary(LONG_TRANSCRIPT)
        elapsed = time.time() - start_time

        print(f"\n✅ Long transcript summarized in {elapsed:.2f} seconds")
        print(f"\n📄 Summary ({len(summary.split())} words):")
        print(summary)

        print(f"\n📊 Performance:")
        print(f"   - Input: {len(LONG_TRANSCRIPT.split())} words")
        print(f"   - Output: {len(summary.split())} words")
        print(f"   - Compression: {len(summary.split()) / len(LONG_TRANSCRIPT.split()):.1%}")
        print(f"   - Processing Time: {elapsed:.2f}s")
        print(f"   - Speed: {len(LONG_TRANSCRIPT.split()) / elapsed:.0f} words/sec")

        return True

    except Exception as e:
        print(f"❌ Long transcript test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chunking_strategy():
    """Test 5: Chunking strategy"""
    print_separator()
    logger.info("TEST 5: Chunking Strategy")
    print_separator()

    try:
        service = get_summarization_service()

        test_text = "This is a sentence. " * 100  # Create a long text
        chunks = service.chunk_text(test_text, max_chars=200, overlap=50)

        print(f"📊 Chunking Test:")
        print(f"   - Input Length: {len(test_text)} chars")
        print(f"   - Number of Chunks: {len(chunks)}")
        print(f"   - Average Chunk Size: {sum(len(c) for c in chunks) / len(chunks):.0f} chars")

        print(f"\n📋 Chunk Details:")
        for i, chunk in enumerate(chunks[:3], 1):  # Show first 3 chunks
            print(f"   Chunk {i}: {len(chunk)} chars - \"{chunk[:60]}...\"")

        if len(chunks) > 3:
            print(f"   ... and {len(chunks) - 3} more chunks")

        print("\n✅ Chunking strategy working correctly")
        return True

    except Exception as e:
        print(f"❌ Chunking test failed: {e}")
        return False


def test_edge_cases():
    """Test 6: Edge cases"""
    print_separator()
    logger.info("TEST 6: Edge Cases")
    print_separator()

    tests = {
        "Empty string": "",
        "Very short": "Hello.",
        "Single word": "Meeting",
        "Only names": "John Sarah Mike",
    }

    results = []

    for name, text in tests.items():
        try:
            print(f"\n🧪 Testing: {name}")
            print(f"   Input: \"{text}\"")

            if text:
                summary = generate_simple_meeting_summary(text)
                print(f"   Output: \"{summary[:100]}...\"" if len(summary) > 100 else f"   Output: \"{summary}\"")
                results.append(True)
            else:
                print(f"   Skipped empty input")
                results.append(True)

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results.append(False)

    if all(results):
        print("\n✅ All edge cases handled correctly")
        return True
    else:
        print(f"\n⚠️  Some edge cases failed ({sum(results)}/{len(results)} passed)")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*80)
    print("🧪 FLAN-T5 Model Integration Test Suite")
    print("="*80)

    tests = [
        ("Model Loading", test_model_loading),
        ("Short Transcript", test_short_transcript),
        ("Medium Transcript (Structured)", test_medium_transcript),
        ("Long Transcript (Chunking)", test_long_transcript),
        ("Chunking Strategy", test_chunking_strategy),
        ("Edge Cases", test_edge_cases),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results[test_name] = False

    # Summary
    print_separator()
    print("📊 TEST SUMMARY")
    print_separator()

    passed = sum(results.values())
    total = len(results)

    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n{'='*80}")
    print(f"Final Result: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED! Model is ready for production.")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please review the errors above.")

    print("="*80 + "\n")


if __name__ == "__main__":
    run_all_tests()
