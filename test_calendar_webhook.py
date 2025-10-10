#!/usr/bin/env python3
"""
Test script for Google Calendar webhook integration
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

async def test_calendar_integration():
    """Test the calendar webhook integration"""
    print("🗓️  Testing Google Calendar Webhook Integration")
    print("=" * 60)
    
    # Get access token (you'll need to get this from the login flow)
    access_token = input("📝 Enter your access token: ").strip()
    
    if not access_token:
        print("❌ Access token is required")
        return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            # Test 1: Check current webhook status
            print("\n1. Checking webhook status...")
            response = await client.get(f"{API_BASE}/calendar/webhook-status", headers=headers)
            
            if response.status_code == 200:
                status = response.json()
                print(f"   ✅ Webhook status: {status}")
            else:
                print(f"   ❌ Failed to get webhook status: {response.status_code}")
                print(f"   Response: {response.text}")
                return
            
            # Test 2: Setup webhook (if not already active)
            if not status.get("webhook_active"):
                print("\n2. Setting up calendar webhook...")
                response = await client.post(f"{API_BASE}/calendar/setup-webhook", headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ Webhook setup successful: {result}")
                else:
                    print(f"   ❌ Failed to setup webhook: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return
            else:
                print("\n2. Webhook already active, skipping setup")
            
            # Test 3: Manual calendar sync
            print("\n3. Performing manual calendar sync...")
            response = await client.post(f"{API_BASE}/calendar/sync", headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Calendar sync successful:")
                print(f"   Message: {result.get('message')}")
                events = result.get('events', [])
                print(f"   Found {len(events)} events with meeting URLs:")
                
                for event in events[:3]:  # Show first 3 events
                    print(f"     - {event.get('title')}")
                    print(f"       Time: {event.get('start_time')}")
                    print(f"       Platform: {event.get('platform')}")
                    print(f"       URL: {event.get('meeting_url')[:50]}...")
                    print()
            else:
                print(f"   ❌ Failed to sync calendar: {response.status_code}")
                print(f"   Response: {response.text}")
                return
            
            # Test 4: Get meetings to verify sync worked
            print("\n4. Checking synchronized meetings...")
            response = await client.get(f"{API_BASE}/meetings/", headers=headers)
            
            if response.status_code == 200:
                meetings = response.json()
                calendar_meetings = [m for m in meetings if m.get('calendar_event_id')]
                print(f"   ✅ Found {len(calendar_meetings)} meetings from calendar:")
                
                for meeting in calendar_meetings[:3]:  # Show first 3
                    print(f"     - {meeting.get('title')}")
                    print(f"       Platform: {meeting.get('platform')}")
                    print(f"       Status: {meeting.get('status')}")
                    print(f"       Calendar Event ID: {meeting.get('calendar_event_id')}")
                    print()
            else:
                print(f"   ❌ Failed to get meetings: {response.status_code}")
                print(f"   Response: {response.text}")
            
            print("\n✅ Calendar integration test completed successfully!")
            print("\nNext steps:")
            print("1. Create a test meeting in your Google Calendar with a Zoom/Meet URL")
            print("2. The webhook should automatically sync it to your meetings")
            print("3. Check the meetings list to see the new meeting appear")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")

async def test_webhook_endpoint():
    """Test the webhook endpoint directly (for debugging)"""
    print("\n🔗 Testing webhook endpoint...")
    
    # Simulate a Google Calendar webhook notification
    test_headers = {
        "X-Goog-Resource-Id": "test_resource_123",
        "X-Goog-Resource-State": "exists",
        "X-Goog-Channel-Token": "1"  # User ID 1
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_BASE}/calendar/webhook", headers=test_headers)
            print(f"Webhook response: {response.status_code}")
            print(f"Response body: {response.json()}")
        except Exception as e:
            print(f"Webhook test error: {e}")

def get_auth_instructions():
    """Show instructions for getting an access token"""
    print("\n📋 How to get an access token:")
    print("1. Go to http://localhost:8000/login")
    print("2. Sign in with Google")
    print("3. Open browser developer tools (F12)")
    print("4. Go to Application > Local Storage > http://localhost:8000")
    print("5. Copy the value of 'access_token'")
    print("6. Paste it when prompted above")

async def main():
    """Main test function"""
    print("Choose a test option:")
    print("1. Full calendar integration test")
    print("2. Test webhook endpoint only") 
    print("3. Show auth instructions")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        await test_calendar_integration()
    elif choice == "2":
        await test_webhook_endpoint()
    elif choice == "3":
        get_auth_instructions()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())