"""
Profile Manager Tests

Tests for UserProfileManager covering:
- Profile creation
- Profile updates with message analysis
- Style summary generation
- Technical term detection
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from rag.profile_manager import UserProfileManager


def test_profile_creation():
    """Test profile creation writes correct structure to disk."""
    print("Test: Profile creation...")

    manager = UserProfileManager(base_path=str(Path(__file__).parent.parent / "data" / "users"))
    user_id = "test_user_profile_create"

    # Delete if exists
    if manager.profile_exists(user_id):
        profile_path = manager._get_profile_path(user_id)
        profile_path.unlink()

    # Create profile
    profile = manager.create_profile(user_id)

    # Verify structure
    assert profile['user_id'] == user_id
    assert 'created_at' in profile
    assert 'speaking_style' in profile
    assert 'conversation_stats' in profile

    # Verify defaults
    assert profile['speaking_style']['formality_level'] in ['casual', 'formal']
    assert profile['conversation_stats']['total_messages'] == 0

    # Cleanup
    manager._get_profile_path(user_id).unlink()
    print("  [OK] PASSED\n")


def test_update_profile_computes_avg_message_length():
    """Test update_profile correctly computes average message length."""
    print("Test: Profile update - message length...")

    manager = UserProfileManager(base_path=str(Path(__file__).parent.parent / "data" / "users"))
    user_id = "test_user_profile_update"

    # Clean start
    if manager.profile_exists(user_id):
        manager._get_profile_path(user_id).unlink()

    profile = manager.create_profile(user_id)

    # Add short messages
    short_messages = ["Hi", "Ok", "Yes thanks"]
    manager.update_profile(user_id, short_messages)

    profile = manager.load_profile(user_id)
    avg_words = profile['speaking_style']['avg_words_per_message']

    # Should be low (these are 1-2 word messages)
    assert avg_words < 5
    assert profile['speaking_style']['avg_message_length'] == "short"

    # Add longer messages
    long_messages = [
        "This is a much longer message with many words in it",
        "Another long message to test the average calculation properly"
    ]
    manager.update_profile(user_id, long_messages)

    profile = manager.load_profile(user_id)
    new_avg = profile['speaking_style']['avg_words_per_message']

    # Average should increase
    assert new_avg > avg_words

    # Cleanup
    manager._get_profile_path(user_id).unlink()
    print("  [OK] PASSED\n")


def test_get_style_summary():
    """Test get_style_summary returns non-empty string."""
    print("Test: Style summary generation...")

    manager = UserProfileManager(base_path=str(Path(__file__).parent.parent / "data" / "users"))
    user_id = "test_user_summary"

    # Clean start
    if manager.profile_exists(user_id):
        manager._get_profile_path(user_id).unlink()

    profile = manager.create_profile(user_id)

    # Add messages
    messages = [
        "I have an error in my code",
        "The model is not loading",
        "How do I fix this bug"
    ]
    manager.update_profile(user_id, messages)

    # Get summary
    summary = manager.get_style_summary(user_id)

    # Verify summary
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert any(word in summary.lower() for word in ['speak', 'user', 'english'])

    # Summary should be concise (under 200 words)
    assert len(summary.split()) < 200

    # Cleanup
    manager._get_profile_path(user_id).unlink()
    print("  [OK] PASSED\n")


def test_technical_term_detection():
    """Test that technical term detection works."""
    print("Test: Technical term detection...")

    manager = UserProfileManager(base_path=str(Path(__file__).parent.parent / "data" / "users"))
    user_id = "test_user_technical"

    # Clean start
    if manager.profile_exists(user_id):
        manager._get_profile_path(user_id).unlink()

    profile = manager.create_profile(user_id)

    # Add technical messages
    technical_messages = [
        "I have an error in my Python code",
        "The neural network model is not training properly",
        "How do I optimize the database query latency"
    ]
    manager.update_profile(user_id, technical_messages)

    profile = manager.load_profile(user_id)

    # Should detect technical terms
    assert profile['speaking_style']['uses_technical_terms'] == True
    assert len(profile['speaking_style']['typical_topics']) > 0

    # Cleanup
    manager._get_profile_path(user_id).unlink()
    print("  [OK] PASSED\n")


def run_all_tests():
    """Run all profile tests."""
    print("=== Running Profile Manager Tests ===\n")

    test_profile_creation()
    test_update_profile_computes_avg_message_length()
    test_get_style_summary()
    test_technical_term_detection()

    print("[OK] All Profile Manager tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
