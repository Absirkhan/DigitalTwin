"""
Setup script for Google Calendar webhooks with ngrok
"""

import os
import sys
import subprocess
import requests
import json
from pathlib import Path

def check_ngrok_installed():
    """Check if ngrok is installed"""
    try:
        subprocess.run(['ngrok', 'version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_ngrok():
    """Start ngrok tunnel"""
    try:
        # Start ngrok in background
        process = subprocess.Popen(['ngrok', 'http', '8000', '--log=stdout'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        # Wait a moment for ngrok to start
        import time
        time.sleep(3)
        
        # Get the public URL
        response = requests.get('http://localhost:4040/api/tunnels')
        tunnels = response.json()
        
        if tunnels['tunnels']:
            public_url = tunnels['tunnels'][0]['public_url']
            return public_url, process
        else:
            return None, None
            
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        return None, None

def update_env_file(webhook_url):
    """Update .env file with webhook URL"""
    env_path = Path('.env')
    
    # Read existing .env content
    env_content = []
    webhook_line_found = False
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('WEBHOOK_BASE_URL='):
                    env_content.append(f'WEBHOOK_BASE_URL={webhook_url}\n')
                    webhook_line_found = True
                else:
                    env_content.append(line)
    
    # Add webhook URL if not found
    if not webhook_line_found:
        env_content.append(f'WEBHOOK_BASE_URL={webhook_url}\n')
    
    # Write back to .env
    with open(env_path, 'w') as f:
        f.writelines(env_content)
    
    print(f"Updated .env file with WEBHOOK_BASE_URL={webhook_url}")

def setup_webhook_with_api(webhook_url, access_token):
    """Setup webhook using the API"""
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post('http://localhost:8000/api/v1/calendar/setup-webhook', 
                               headers=headers)
        
        if response.status_code == 200:
            print("✅ Webhook setup successful!")
            print(f"Webhook URL: {webhook_url}/api/v1/calendar/webhook")
            return True
        else:
            print(f"❌ Webhook setup failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error setting up webhook: {e}")
        return False

def main():
    print("🔧 Google Calendar Webhook Setup")
    print("=" * 40)
    
    # Check if ngrok is installed
    if not check_ngrok_installed():
        print("❌ ngrok is not installed or not in PATH")
        print("📥 Please install ngrok from https://ngrok.com/download")
        print("   After installation, add ngrok to your PATH")
        return
    
    print("✅ ngrok is installed")
    
    # Start ngrok
    print("🚀 Starting ngrok tunnel...")
    public_url, process = start_ngrok()
    
    if not public_url:
        print("❌ Failed to start ngrok tunnel")
        return
    
    print(f"✅ ngrok tunnel started: {public_url}")
    
    # Update .env file
    update_env_file(public_url)
    
    # Get access token from user
    print("\n🔑 To setup the webhook, you need your access token")
    print("You can get it by:")
    print("1. Going to http://localhost:8000/login")
    print("2. Signing in with Google")
    print("3. Copying the access token from the browser's localStorage")
    print("   (Open DevTools > Application > Local Storage > access_token)")
    
    access_token = input("\n📝 Enter your access token (or press Enter to skip): ").strip()
    
    if access_token:
        print("\n🔗 Setting up webhook...")
        success = setup_webhook_with_api(public_url, access_token)
        
        if success:
            print("\n🎉 Setup complete!")
            print("Your webhook is now active and will receive calendar notifications")
        else:
            print("\n⚠️ Webhook setup failed, but ngrok is running")
            print("You can manually setup the webhook later using:")
            print(f"POST http://localhost:8000/api/v1/calendar/setup-webhook")
    else:
        print("\n⏭️ Skipping webhook setup")
        print("You can setup the webhook later using:")
        print(f"POST http://localhost:8000/api/v1/calendar/setup-webhook")
    
    print(f"\n📍 Your webhook URL is: {public_url}/api/v1/calendar/webhook")
    print("🔄 Restart your FastAPI server to pick up the new webhook URL")
    print("⚠️ Keep this terminal open to maintain the ngrok tunnel")
    
    # Keep the process running
    try:
        input("\nPress Enter to stop ngrok tunnel...")
        if process:
            process.terminate()
            print("🛑 ngrok tunnel stopped")
    except KeyboardInterrupt:
        if process:
            process.terminate()
            print("\n🛑 ngrok tunnel stopped")

if __name__ == "__main__":
    main()