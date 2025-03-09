import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Hard-coded API URL
POST_PITCH_API_URL = "https://post-pitch-fork.onrender.com/"

# Import the template maker module
from src.backlink_agent import template_maker

class EmailCreator:
    def __init__(self):
        """
        Initialize the EmailCreator.
        """
        # We'll set the template in create_emails
        self.outreach_template = None
    
    def _get_post_pitch(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Call the post pitch API for a single URL.
        
        Args:
            url: The target website URL
            
        Returns:
            Dictionary with API response or None if the request failed
        """
        try:
            # Format the API endpoint with the URL parameter
            api_endpoint = f"{POST_PITCH_API_URL}email_data_lenient?url={url}"
            
            response = requests.get(
                api_endpoint,
                timeout=60  # Increased timeout as this API might take longer
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error getting post pitch for {url}: {str(e)}")
            return None
    
    def create_emails(self, urls: List[str], site_id: int) -> List[Dict[str, str]]:
        """
        Create personalized emails for a list of URLs.
        
        Args:
            urls: List of target website URLs
            site_id: Integer ID of the site to use for template generation
            
        Returns:
            List of email objects with subject, body, and recipient email
        """
        # Create an instance of TemplateMaker and call its create_template method
        template_maker_instance = template_maker.TemplateMaker()
        self.outreach_template = template_maker_instance.create_template(site_id)
        
        emails = []
        
        for url in urls:
            pitch_data = self._get_post_pitch(url)
            
            if not pitch_data or "error" in pitch_data:
                logger.warning(f"Failed to get pitch data for {url}")
                continue
            
            # Extract necessary information from pitch_data
            try:
                subject = pitch_data.get("subject", "")
                personalization = pitch_data.get("body", "")
                recipient_email = pitch_data.get("email", "")
                
                # Skip if any required field is missing
                if not all([subject, personalization, recipient_email]):
                    logger.warning(f"Missing required data for {url}")
                    continue
                
                # Combine personalization with the outreach template
                full_body = f"{personalization}\n\n{self.outreach_template}"
                
                emails.append({
                    "subject": subject,
                    "body": full_body,
                    "email": recipient_email
                })
                
            except Exception as e:
                logger.error(f"Error processing pitch data for {url}: {str(e)}")
                continue
        
        return emails


# Example usage:
def create_outreach_emails(urls: List[str], template: str) -> List[Dict[str, str]]:
    """
    Convenience function to create outreach emails.
    
    Args:
        urls: List of target website URLs
        template: Static template to append to each personalized message
        
    Returns:
        List of email objects with subject, body, and recipient email
    """
    creator = EmailCreator()
    return creator.create_emails(urls)


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create an instance of EmailCreator
    creator = EmailCreator()
    
    # Test URLs
    test_urls = [
        "https://mashable.com",
        "https://techcrunch.com",
        "https://wired.com"
    ]
    
    print(f"Testing email creation with {len(test_urls)} URLs...")
    
    # First test the individual API call
    print("\nTesting individual API call with mashable.com:")
    result = creator._get_post_pitch(test_urls[0])
    if result:
        print("API call successful!")
        print("Response:")
        import json
        print(json.dumps(result, indent=2))
    else:
        print("API call failed. Check logs for details.")
    
    # Now test the full email creation
    print("\nTesting full email creation:")
    emails = creator.create_emails(test_urls, 1)
    
    print(f"\nCreated {len(emails)} emails out of {len(test_urls)} URLs")
    
    # Print the first email as an example
    if emails:
        print("\nExample email:")
        print(f"To: {emails[0]['email']}")
        print(f"Subject: {emails[0]['subject']}")
        print(f"Body:\n{emails[0]['body']}")
