"""
Auto-join service manager
Handles starting and monitoring the Celery worker and beat scheduler for auto-join functionality
"""

import subprocess
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

class AutoJoinManager:
    def __init__(self):
        self.worker_process = None
        self.beat_process = None
        self.project_root = Path(__file__).parent.parent.parent
        
    def start_worker(self):
        """Start Celery worker"""
        try:
            cmd = [
                sys.executable, "-m", "celery", 
                "-A", "app.core.celery:celery_app", 
                "worker", 
                "--loglevel=info",
                "--concurrency=2"
            ]
            
            self.worker_process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Celery worker started with PID: {self.worker_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Celery worker: {str(e)}")
            return False
    
    def start_beat(self):
        """Start Celery beat scheduler"""
        try:
            cmd = [
                sys.executable, "-m", "celery",
                "-A", "app.core.celery:celery_app",
                "beat",
                "--loglevel=info"
            ]
            
            self.beat_process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Celery beat started with PID: {self.beat_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Celery beat: {str(e)}")
            return False
    
    def start_all(self):
        """Start both worker and beat"""
        worker_started = self.start_worker()
        beat_started = self.start_beat()
        
        return worker_started and beat_started
    
    def stop_worker(self):
        """Stop Celery worker"""
        if self.worker_process:
            try:
                self.worker_process.terminate()
                self.worker_process.wait(timeout=10)
                logger.info("Celery worker stopped")
                return True
            except Exception as e:
                logger.error(f"Failed to stop Celery worker: {str(e)}")
                return False
        return True
    
    def stop_beat(self):
        """Stop Celery beat"""
        if self.beat_process:
            try:
                self.beat_process.terminate()
                self.beat_process.wait(timeout=10)
                logger.info("Celery beat stopped")
                return True
            except Exception as e:
                logger.error(f"Failed to stop Celery beat: {str(e)}")
                return False
        return True
    
    def stop_all(self):
        """Stop both worker and beat"""
        worker_stopped = self.stop_worker()
        beat_stopped = self.stop_beat()
        
        return worker_stopped and beat_stopped
    
    def is_running(self):
        """Check if services are running"""
        worker_running = self.worker_process and self.worker_process.poll() is None
        beat_running = self.beat_process and self.beat_process.poll() is None
        
        return {
            "worker": worker_running,
            "beat": beat_running,
            "both": worker_running and beat_running
        }

# Global manager instance
auto_join_manager = AutoJoinManager()