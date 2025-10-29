#!/usr/bin/env python3
"""
Quick test script to verify the summarization service works
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.summarization import generate_simple_meeting_summary

# Test transcript (short example)
test_transcript = """
i221345 Rihab Rabbani: Of the, today's topic is the discussion about the sprint. One of our final year\ni221345 Rihab Rabbani: project.\ni221345 Rihab Rabbani: How are you doing?\ni220915 Absir Ahmed: I am doing good.\ni220915 Absir Ahmed: How are you doing, upset?\ni220915 Absir Ahmed: oh,\ni221345 Rihab Rabbani: I am also good up, sir.\ni221345 Rihab Rabbani: So basically my part has been done on this project and my part was to work on\ni221345 Rihab Rabbani: the fast API of this project.\ni221345 Rihab Rabbani: And I developed the backend in Python and I created all the endpoints here.\ni221345 Rihab Rabbani: Regarding the board meeting joining and the boards transcript and the boards\ni221345 Rihab Rabbani: recording URL as well.\ni221345 Rihab Rabbani: And the board automatically joins the meeting once it is added, once the meeting\ni221345 Rihab Rabbani: is added in the Google calendar.\ni220915 Absir Ahmed: That sounds pretty good. What about the database integration? Has that been\ni220915 Absir Ahmed: done?\ni221345 Rihab Rabbani: Yes, that has been done as well and all the tables are configured and the\ni221345 Rihab Rabbani: schemas have been configured as well.\ni221345 Rihab Rabbani: So everything is up to date and we're going at the perfect pace as we should.\ni220915 Absir Ahmed: so, as the documentation been completed as well, because as far as I remember,\ni220915 Absir Ahmed: we were quite slow on\ni221345 Rihab Rabbani: Know that part has been done as well and everything is up to date. As of now\ni221345 Rihab Rabbani: What's the update on your part regarding the model that we were using?\ni220915 Absir Ahmed: The model that we were using has been done as well and it has been fine-tuned\ni220915 Absir Ahmed: and everything is working perfectly. It has been configured with our project as\ni220915 Absir Ahmed: well.\ni221345 Rihab Rabbani: Just that sounds amazing. So I guess that's basically it. Everything is\ni221345 Rihab Rabbani: completed and everything is done.\ni221345 Rihab Rabbani: so,\ni221345 Rihab Rabbani: I think we should call it a day.\ni221345 Rihab Rabbani: And let's rest and meet on Friday and further discuss things. If I'm not wrong,\ni221345 Rihab Rabbani: the front end, has to be done by you.\ni220915 Absir Ahmed: Yes, I'm the one who's going to work on the front end for this project. So I'll\ni220915 Absir Ahmed: let you know when that has been done as well.\ni221345 Rihab Rabbani: Okay, that sounds great. Thank you. Good.\ni220915 Absir Ahmed: Take care, goodbye.
"""

def test_summarization():
    """Test the summarization service"""
    print("=" * 60)
    print("Testing Summarization Service")
    print("=" * 60)
    
    try:
        print(f"\n📝 Input transcript ({len(test_transcript.split())} words):")
        print(test_transcript)
        
        print("\n⏳ Generating summary...")
        summary = generate_simple_meeting_summary(test_transcript)
        
        print(f"\n✅ Summary generated successfully!")
        print(f"\n📋 Summary ({len(summary.split())} words):")
        print(summary)
        
        # Calculate compression ratio
        input_words = len(test_transcript.split())
        output_words = len(summary.split())
        compression = (output_words / input_words) * 100
        
        print(f"\n📊 Statistics:")
        print(f"   Input:       {input_words} words")
        print(f"   Output:      {output_words} words")
        print(f"   Compression: {compression:.1f}%")
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_summarization()
