#!/usr/bin/env python3
"""
Google OAuth Setup Script for Digital Twin
"""

import os
import json
from pathlib import Path

def create_env_file():
    """Create .env file from template"""
    template_path = Path(".env.template")
    env_path = Path(".env")
    
    if not template_path.exists():
        print("❌ .env.template file not found!")
        return False
    
    if env_path.exists():
        response = input("📄 .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("✅ Keeping existing .env file")
            return True
    
    # Copy template to .env
    with open(template_path, 'r') as template:
        content = template.read()
    
    with open(env_path, 'w') as env_file:
        env_file.write(content)
    
    print("✅ Created .env file from template")
    return True

def setup_google_oauth():
    """Guide user through Google OAuth setup"""
    print("\n🔐 Google OAuth Setup")
    print("=" * 50)
    
    print("\n1. Go to Google Cloud Console:")
    print("   https://console.cloud.google.com/")
    
    print("\n2. Create a new project or select an existing one")
    
    print("\n3. Enable required APIs:")
    print("   - Google+ API")
    print("   - Gmail API")
    print("   - Google Calendar API")
    
    print("\n4. Create OAuth 2.0 Client ID:")
    print("   - Go to Credentials > Create Credentials > OAuth 2.0 Client ID")
    print("   - Application type: Web application")
    print("   - Authorized redirect URIs:")
    print("     http://localhost:8000/api/v1/auth/google/callback")
    
    print("\n5. Download the client configuration or copy the credentials")
    
    client_id = input("\n📝 Enter your Google Client ID: ").strip()
    client_secret = input("📝 Enter your Google Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Both Client ID and Client Secret are required!")
        return False
    
    # Update .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found! Please run the setup first.")
        return False
    
    # Read current .env content
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update Google OAuth settings
    updated_lines = []
    for line in lines:
        if line.startswith('GOOGLE_CLIENT_ID='):
            updated_lines.append(f'GOOGLE_CLIENT_ID={client_id}\n')
        elif line.startswith('GOOGLE_CLIENT_SECRET='):
            updated_lines.append(f'GOOGLE_CLIENT_SECRET={client_secret}\n')
        else:
            updated_lines.append(line)
    
    # Write updated content
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    print("✅ Updated .env file with Google OAuth credentials")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'fastapi',
        'google-auth',
        'google-auth-oauthlib',
        'google-api-python-client',
        'python-jose',
        'sqlalchemy',
        'alembic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📥 Install missing packages:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def run_database_migration():
    """Run database migration"""
    print("\n🗄️ Running database migration...")
    
    try:
        os.system("alembic upgrade head")
        print("✅ Database migration completed")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Digital Twin Google OAuth Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("app").exists() or not Path("requirements.txt").exists():
        print("❌ Please run this script from the DigitalTwin root directory")
        return
    
    # Step 1: Create .env file
    if not create_env_file():
        return
    
    # Step 2: Check dependencies
    if not check_dependencies():
        print("\n⚠️ Please install missing dependencies first")
        return
    
    # Step 3: Setup Google OAuth
    if not setup_google_oauth():
        return
    
    # Step 4: Run database migration
    if not run_database_migration():
        print("\n⚠️ Database migration failed. You may need to set up the database first.")
    
    print("\n🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Start the application: uvicorn app.main:app --reload")
    print("2. Visit http://localhost:8000 to test Google OAuth")
    print("3. Check the login page at http://localhost:8000/login")

if __name__ == "__main__":
    main()