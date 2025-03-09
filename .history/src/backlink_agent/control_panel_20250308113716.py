import logging
import random
from typing import List, Dict, Any, Optional

from .prospect_generator import ProspectGenerator
from .email_creator import EmailCreator
from .email_sender import EmailSender

logger = logging.getLogger(__name__)

class ControlPanel:
    def __init__(
        self, 
        prospect_generator: ProspectGenerator,
        email_creator: EmailCreator,
        email_sender: EmailSender,
        max_emails: int = 5
    ):
        """
        Initialize the ControlPanel with necessary components.
        
        Args:
            prospect_generator: Component to generate prospect URLs
            email_creator: Component to create personalized emails
            email_sender: Component to send emails
            max_emails: Maximum number of emails to send in one batch
        """
        self.prospect_generator = prospect_generator
        self.email_creator = email_creator
        self.email_sender = email_sender
        self.max_emails = 5
    
    def run_outreach_campaign(self, query: str) -> Dict[str, Any]:
        """
        Run a complete outreach campaign from prospecting to sending emails.
        
        Args:
            query: Search query to find prospects
            
        Returns:
            Dictionary with campaign results
        """
        logger.info(f"Starting outreach campaign for query: {query}")
        
        # Step 1: Generate prospects
        prospects = self.prospect_generator.generate_prospects(query)
        logger.info(f"Generated {len(prospects)} prospects")
        
        if not prospects:
            return {"status": "failed", "reason": "No prospects found", "emails_sent": 0}
        
        # Step 2: Shuffle and limit prospects
        random.shuffle(prospects)
        selected_prospects = prospects[:self.max_emails]
        logger.info(f"Selected {len(selected_prospects)} prospects for outreach")
        
        # Step 3: Create personalized emails
        emails = self.email_creator.create_emails(selected_prospects)
        logger.info(f"Created {len(emails)} personalized emails")
        
        if not emails:
            return {"status": "failed", "reason": "No emails could be created", "emails_sent": 0}
        
        # Step 4: Send emails one by one
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
        
        # Return campaign results
        return {
            "status": "completed",
            "total_prospects": len(prospects),
            "selected_prospects": len(selected_prospects),
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
    
    prospect_generator = ProspectGenerator()
    email_creator = EmailCreator()
    email_sender = EmailSender()
    
    return ControlPanel(
        prospect_generator=prospect_generator,
        email_creator=email_creator,
        email_sender=email_sender,
        max_emails=max_emails
    )


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create control panel with default components
    control_panel = create_default_control_panel()  # Limit to 3 for testing
    
    # Run a test campaign
    test_query = "digital marketing blogs"
    
    print(f"Running test outreach campaign for query: '{test_query}'")
    result = control_panel.run_outreach_campaign(test_query)
    
    print("\nCampaign Results:")
    for key, value in result.items():
        print(f"{key}: {value}") 