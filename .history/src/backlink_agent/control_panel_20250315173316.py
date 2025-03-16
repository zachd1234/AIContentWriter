import os
import sys

# Get the absolute path to the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the project root to Python's path if it's not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Make sure api module can be found
api_path = os.path.join(project_root, 'src', 'api')
if os.path.exists(api_path) and api_path not in sys.path:
    sys.path.insert(0, api_path)

# Import after setting up the path
import logging
import random
import json
from typing import List, Dict, Any, Optional

# Use absolute imports instead of relative imports
from src.backlink_agent.prospect_generator import ProspectGenerator
from src.backlink_agent.email_creator import EmailCreator
from src.backlink_agent.email_sender import EmailSender
from src.database_service import DatabaseService

logger = logging.getLogger(__name__)

class ControlPanel:
    def __init__(
        self, 
        prospect_generator: ProspectGenerator,
        email_creator: EmailCreator,
        email_sender: EmailSender,
        database_service,
        max_emails: int = 10
    ):
        """
        Initialize the ControlPanel with necessary components.
        
        Args:
            prospect_generator: Component to generate prospect URLs
            email_creator: Component to create personalized emails
            email_sender: Component to send emails
            database_service: Service to manage URLs in the database
            max_emails: Maximum number of emails to send in one batch
        """
        self.prospect_generator = prospect_generator
        self.email_creator = email_creator
        self.email_sender = email_sender
        self.database_service = database_service
        self.max_emails = max_emails
    
    def run_outreach_campaign(self, site_id: int) -> Dict[str, Any]:
        """
        Run a complete outreach campaign using URLs from the database.
        
        Args:
            site_id: Integer ID of the site to use for template generation
            
        Returns:
            Dictionary with campaign results
        """
        logger.info(f"Starting outreach campaign for site ID: {site_id}")
        
        # Step 1: Get prospects from database
        prospects = self.database_service.pop_next_urls(self.max_emails, site_id)
        logger.info(f"Retrieved {len(prospects)} prospects from database")
        print(f"\n===== PROSPECTS RETRIEVED =====")
        for i, prospect in enumerate(prospects):
            print(f"Prospect {i+1}:")
            print(json.dumps(prospect, indent=2))
        print("==============================\n")
        
        if not prospects:
            return {"status": "failed", "reason": "No prospects available in database", "emails_sent": 0}
        
        # Step 2: Extract just the URLs from the prospects
        prospect_urls = [prospect['url'] for prospect in prospects]
        print(f"\n===== EXTRACTED URLS =====")
        for i, url in enumerate(prospect_urls):
            print(f"URL {i+1}: {url}")
        print("==============================\n")
        
        # Step 3: Create personalized emails with site_id
        print(f"\n===== CREATING EMAILS =====")
        emails = self.email_creator.create_emails(prospect_urls, site_id)
        logger.info(f"Created {len(emails)} personalized emails")
        print(f"Created {len(emails)} personalized emails")
        
        if emails:
            print("\n===== EMAILS CREATED =====")
            for i, email in enumerate(emails):
                print(f"Email {i+1}:")
                print(f"To: {email.get('email', 'No email address')}")
                print(f"Subject: {email.get('subject', 'No subject')}")
                print(f"Body:\n{email.get('body', 'No body')}")
                print("----------------------------")
        else:
            print("No emails were created!")
        print("==============================\n")
        
        if not emails:
            return {"status": "failed", "reason": "No emails could be created", "emails_sent": 0}
        
        # Step 4: Send emails one by one
        successful_sends = 0
        failed_sends = 0
        
        print("\n===== SENDING EMAILS =====")
        for i, email in enumerate(emails):
            try:
                print(f"Sending email {i+1} to {email['email']}...")
                result = self.email_sender.send_backlink_outreach_email(
                    to_email=email["email"],
                    subject=email["subject"],
                    body=email["body"],
                    site_id=site_id
                )
                
                if result.get("success", False):
                    successful_sends += 1
                    logger.info(f"Successfully sent email to {email['email']}")
                    print(f"✅ Successfully sent email to {email['email']}: {result.get('message', 'Email sent')}")
                else:
                    failed_sends += 1
                    logger.warning(f"Failed to send email to {email['email']}: {result.get('message', 'Unknown error')}")
                    print(f"❌ Failed to send email to {email['email']}: {result.get('message', 'Unknown error')}")
                
            except Exception as e:
                failed_sends += 1
                logger.error(f"Error sending email to {email['email']}: {str(e)}")
                print(f"❌ Error sending email to {email['email']}: {str(e)}")
        print("==============================\n")
        
        logger.info(f"Processed {len(prospects)} prospects")
        
        # Return campaign results
        return {
            "status": "completed",
            "prospects_used": len(prospects),
            "emails_created": len(emails),
            "emails_sent": successful_sends,
            "emails_failed": failed_sends
        }

    def setup_outreach(self, site_id: int) -> Dict[str, Any]:
        """
        Set up outreach by clearing existing prospect URLs and generating new ones.
        
        This control panel method:
        1. Retrieves blog information from the database
        2. Clears all existing prospect URLs for the specified site_id
        3. Generates a new complete prospect report
        4. Saves the new prospects to the database
        
        Args:
            site_id: ID of the site to clear and update prospects for
            
        Returns:
            A complete prospect report with all categories and websites
        """
        # Step 1: Get blog information from the database
        print(f"\n=== RETRIEVING BLOG INFO FOR SITE ID {site_id} ===")
        blog_info = self.database_service.get_blog_info(site_id)
        blog_title = blog_info.get('blog_name') or blog_info.get('topic', '')
        blog_description = blog_info.get('description', '')
        print(f"Retrieved blog info: {blog_title} - {blog_description[:50]}...")
        
        # Step 2: Clear existing prospect URLs for this site
        print(f"\n=== CLEARING EXISTING PROSPECT URLS FOR SITE ID {site_id} ===")
        clear_result = self.database_service.delete_urls_by_site_id(site_id)
        print(f"Cleared {clear_result.get('deleted_count', 0)} existing prospect URLs")
        
        # Step 3: Generate new prospect report using the prospect generator
        print("\n=== GENERATING NEW PROSPECT REPORT ===")
        report = self.prospect_generator.generate_complete_prospect_report(blog_title, blog_description, site_id)
        
        # Return the complete results
        return report

    def has_outreach_prospects(self, site_id):
        """Check if there are any outreach prospects for the given site_id"""
        return self.database_service.has_outreach_prospects(site_id)

    def send_daily_stats_report(self, admin_email: str = "ruckquest@gmail.com") -> Dict[str, Any]:
        """
        Send a daily statistics report email.
        Only sends one report per day.
        
        Args:
            admin_email: Email address to send the report to
            
        Returns:
            Dictionary with status and message
        """
        try:
            import os
            import time
            from datetime import datetime, timedelta
            from pathlib import Path
            
            # Create a timestamp file path
            timestamp_dir = Path(__file__).resolve().parent.parent.parent / "data"
            timestamp_file = timestamp_dir / "last_stats_report.txt"
            
            # Create directory if it doesn't exist
            os.makedirs(timestamp_dir, exist_ok=True)
            
            # Check if we already sent a report today
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            if timestamp_file.exists():
                with open(timestamp_file, "r") as f:
                    last_date = f.read().strip()
                    
                if last_date == current_date:
                    return {
                        "success": True,
                        "message": f"Stats report already sent today to {admin_email}",
                        "skipped": True
                    }
            
            # If we get here, we need to send the report
            from src.backlink_agent.email_sender import EmailSender
            
            # Create email sender
            email_sender = EmailSender()
            
            # Send the report
            result = email_sender.send_stats_report(
                to_email=admin_email,
                site_id=None,  # Send stats for all sites
                days_to_show=5,
                include_recent_emails=True
            )
            
            # Update the timestamp file
            with open(timestamp_file, "w") as f:
                f.write(current_date)
            
            return {
                "success": result.get("success", False),
                "message": f"Stats report sent to {admin_email}",
                "details": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send stats report: {str(e)}"
            }

    def run_advanced_outreach_campaign(self, site_id: int, post_url: str, post_title: str) -> Dict[str, Any]:
        """
        Run an advanced outreach campaign using URLs from the database and specific post information.
        
        Args:
            site_id: Integer ID of the site to use for template generation
            post_url: URL of the specific post to promote in the outreach
            post_title: Title of the specific post to promote
            
        Returns:
            Dictionary with campaign results
        """
        
        best_category, prospects = self.prospect_generator.get_category_list(
            post_url=post_url, 
            post_title=post_title,
            site_id=site_id,
            num_urls=self.max_emails
        )
        
        # Return campaign results
        return {}

def create_default_control_panel(max_emails: int = 10) -> ControlPanel:
    """
    Create a ControlPanel with default components.
    
    Args:
        max_emails: Maximum number of emails to send in one batch
        
    Returns:
        Configured ControlPanel instance
    """
    # Use absolute imports here too
    from src.backlink_agent.prospect_generator import ProspectGenerator
    from src.backlink_agent.email_creator import EmailCreator
    from src.backlink_agent.email_sender import EmailSender
    from src.database_service import DatabaseService
    
    prospect_generator = ProspectGenerator()
    email_creator = EmailCreator()
    email_sender = EmailSender()
    database_service = DatabaseService()
    
    return ControlPanel(
        prospect_generator=prospect_generator,
        email_creator=email_creator,
        email_sender=email_sender,
        database_service=database_service,
        max_emails=max_emails
    )


def main():
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create control panel with default components
    control_panel = create_default_control_panel()  
    
    # Run a test campaign
    test_site_id = 1
    
    print(f"Running test outreach campaign for site ID: {test_site_id}")
    result = control_panel.run_outreach_campaign(test_site_id)
    
    print("\nCampaign Results:")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main() 