"""
Automatic webhook setup service
"""

import asyncio
import subprocess
import requests
import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class WebhookAutoSetup:
    """Automatically manage ngrok and webhook setup"""
    
    def __init__(self):
        self.ngrok_process = None
        self.ngrok_url = None
        self.webhook_active = False
        
    async def auto_setup_for_demo(self) -> Dict[str, Any]:
        """Automatically set up everything needed for webhook demo"""
        try:
            # Check if we're already using a public URL
            if self._is_public_url(settings.WEBHOOK_BASE_URL):
                logger.info(f"Using existing public webhook URL: {settings.WEBHOOK_BASE_URL}")
                return {
                    "status": "ready",
                    "webhook_url": settings.WEBHOOK_BASE_URL,
                    "message": "Using existing public URL"
                }
            
            # Check if ngrok is available
            if not self._is_ngrok_available():
                return {
                    "status": "manual_setup_required",
                    "message": "ngrok not available - manual webhook setup required",
                    "instructions": [
                        "1. Install ngrok from https://ngrok.com/",
                        "2. Run: ngrok http 8000",
                        "3. Update WEBHOOK_BASE_URL in .env with the ngrok URL",
                        "4. Restart the server"
                    ]
                }
            
            # Start ngrok automatically
            public_url = await self._start_ngrok()
            if not public_url:
                return {
                    "status": "failed",
                    "message": "Failed to start ngrok tunnel"
                }
            
            # Update environment
            self._update_webhook_url(public_url)
            
            return {
                "status": "ready",
                "webhook_url": public_url,
                "message": "Ngrok tunnel started and webhook URL updated",
                "demo_ready": True
            }
            
        except Exception as e:
            logger.error(f"Error in auto setup: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _is_public_url(self, url: str) -> bool:
        """Check if URL is publicly accessible"""
        return url and not any(x in url for x in ['localhost', '127.0.0.1', '0.0.0.0'])
    
    def _is_ngrok_available(self) -> bool:
        """Check if ngrok is installed and available"""
        try:
            result = subprocess.run(['ngrok', 'version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return False
    
    async def _start_ngrok(self) -> Optional[str]:
        """Start ngrok tunnel and return public URL"""
        try:
            # Kill any existing ngrok processes
            subprocess.run(['pkill', '-f', 'ngrok'], 
                         capture_output=True, 
                         check=False)
            
            # Start ngrok
            self.ngrok_process = subprocess.Popen(
                ['ngrok', 'http', '8000', '--log=stdout'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for ngrok to start
            await asyncio.sleep(3)
            
            # Get the public URL
            try:
                response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
                tunnels = response.json()
                
                if tunnels.get('tunnels'):
                    public_url = tunnels['tunnels'][0]['public_url']
                    self.ngrok_url = public_url
                    logger.info(f"Ngrok tunnel started: {public_url}")
                    return public_url
                    
            except requests.RequestException:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error starting ngrok: {e}")
            return None
    
    def _update_webhook_url(self, url: str):
        """Update webhook URL in memory (for current session)"""
        # Update the settings object directly
        settings.WEBHOOK_BASE_URL = url
        logger.info(f"Updated webhook URL to: {url}")
    
    def cleanup(self):
        """Clean up ngrok process"""
        if self.ngrok_process:
            try:
                self.ngrok_process.terminate()
                self.ngrok_process.wait(timeout=5)
                logger.info("Ngrok process terminated")
            except subprocess.TimeoutExpired:
                self.ngrok_process.kill()
                logger.warning("Ngrok process killed (timeout)")
            except Exception as e:
                logger.error(f"Error cleaning up ngrok: {e}")


# Global instance
webhook_auto_setup = WebhookAutoSetup()