#!/usr/bin/env python3
"""
Setup script for Digital Twin project
"""

import os
import subprocess
import sys


def run_command(command, exit_on_error=True):
    """Run shell command"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        if exit_on_error:
            sys.exit(1)
        return None
    return result.stdout


def main():
    """Main setup function"""
    print("Setting up Digital Twin project...")
    
    # Create necessary directories
    directories = [
        "models/weights",
        "recordings/temp",
        "recordings/uploads",
        "recordings/generated",
        "data/vectordb",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Copy environment file
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            # Use cross-platform file copy
            import shutil
            shutil.copy(".env.example", ".env")
            print("Created .env file from .env.example")
        else:
            print("Warning: .env.example not found")
    
    # Install dependencies
    print("Installing Python dependencies...")
    
    # First upgrade pip
    print("Upgrading pip...")
    run_command("python -m pip install --upgrade pip", exit_on_error=False)
    
    # Try minimal requirements first to get basic app running
    if os.path.exists("requirements-minimal.txt"):
        print("Installing minimal dependencies to get app running...")
        result = run_command("pip install -r requirements-minimal.txt", exit_on_error=False)
        if result is not None:
            print("✓ Minimal dependencies installed successfully!")
            print("You can install additional AI/ML features later using INSTALL_GUIDE.md")
        else:
            print("Minimal installation failed. Please check INSTALL_GUIDE.md for manual installation.")
    else:
        print("Installing from requirements.txt...")
        run_command("pip install -r requirements.txt", exit_on_error=False)
    
    # Initialize database (optional - might fail if DB not set up)
    print("Initializing database...")
    db_result = run_command("alembic upgrade head", exit_on_error=False)
    if db_result is None:
        print("Database initialization failed. Make sure PostgreSQL is running and configured in .env")
    
    print("Setup complete!")
    print("\nNext steps:")
    print("1. Update .env file with your configuration")
    print("2. Start the application with: uvicorn app.main:app --reload")
    print("3. Start Celery worker with: celery -A app.core.celery worker --loglevel=info")


if __name__ == "__main__":
    main()