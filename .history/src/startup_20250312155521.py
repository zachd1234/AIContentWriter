"""
Startup script for the project - run this when opening the codebase.
"""
import logging
from datetime import datetime
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_daily_report():
    """Send a daily stats report"""
    logger.info("Sending daily stats report...")
    
    # Add the parent directory to sys.path if needed
    src_dir = Path(__file__).resolve().parent
    if str(src_dir) not in sys.path:
        sys.path.append(str(src_dir))
    
    try:
        from backlink_agent.email_sender import EmailSender
        
        # Create email sender
        email_sender = EmailSender()
        
        # Your email address
        admin_email = "your-email@example.com"  # Replace with your email
        
        # Send the report
        result = email_sender.send_stats_report(
            to_email=admin_email,
            site_id=None,  # Set to a specific site ID or None for all sites
            days_to_show=5,
            include_recent_emails=True
        )
        
        if result.get("success", False):
            logger.info("Daily stats report sent successfully")
        else:
            logger.error(f"Failed to send daily stats report: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error sending daily stats report: {str(e)}")

if __name__ == "__main__":
    print("=" * 50)
    print("RUNNING PROJECT STARTUP SCRIPT")
    print("=" * 50)
    send_daily_report()
    print("Startup complete!") 