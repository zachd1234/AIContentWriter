import os
import sys

# Get the absolute path to the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the project root to Python's path if it's not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the API patch to fix import issues
from src.api_patch import *

# Make sure api module can be found
api_path = os.path.join(project_root, 'src', 'api')
if os.path.exists(api_path) and api_path not in sys.path:
    sys.path.insert(0, api_path)

# Import after setting up the path
import logging
import random
from typing import List, Dict, Any, Optional

# Now use relative imports for modules within the same package
from src.backlink_agent.prospect_generator import ProspectGenerator
from .email_creator import EmailCreator
from .email_sender import EmailSender
from src.database_service import DatabaseService

logger = logging.getLogger(__name__)

class ControlPanel:
    def __init__(
        self, 
        prospect_generator: ProspectGenerator,
        email_creator: EmailCreator,
        email_sender: EmailSender,
        database_service,
        max_emails: int = 5
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
        self.max_emails = 5
    
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
        
        if not prospects:
            return {"status": "failed", "reason": "No prospects available in database", "emails_sent": 0}
        
        # Step 2: Create personalized emails with site_id
        emails = self.email_creator.create_emails(prospects, site_id)
        logger.info(f"Created {len(emails)} personalized emails")
        
        if not emails:
            return {"status": "failed", "reason": "No emails could be created", "emails_sent": 0}
        
        # Step 3: Send emails one by one
        successful_sends = 0
        failed_sends = 0
        
        for email in emails:
            try:
                result = self.email_sender.send_email(
                    recipient_email=email["email"],
                    subject=email["subject"],
                    body=email["body"]
                )
                
                if result.get("status") == "success":
                    successful_sends += 1
                    logger.info(f"Successfully sent email to {email['email']}")
                else:
                    failed_sends += 1
                    logger.warning(f"Failed to send email to {email['email']}: {result.get('reason')}")
                
            except Exception as e:
                failed_sends += 1
                logger.error(f"Error sending email to {email['email']}: {str(e)}")
        
        # Step 4: Add used prospects back to the end of the list
        self.database_service.add_urls_to_end(prospects)
        logger.info(f"Added {len(prospects)} prospects back to the end of the database queue")
        
        # Return campaign results
        return {
            "status": "completed",
            "prospects_used": len(prospects),
            "emails_created": len(emails),
            "emails_sent": successful_sends,
            "emails_failed": failed_sends
        }


def create_default_control_panel(max_emails: int = 5) -> ControlPanel:
    """
    Create a ControlPanel with default components.
    
    Args:
        max_emails: Maximum number of emails to send in one batch
        
    Returns:
        Configured ControlPanel instance
    """
    from .prospect_generator import ProspectGenerator
    from .email_creator import EmailCreator
    from .email_sender import EmailSender
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