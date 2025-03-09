import requests
import logging
import importlib.util
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Hard-coded API URL
POST_PITCH_API_URL = "https://post-pitch-fork.onrender.com/"

# Import template_maker directly using importlib
template_maker_path = os.path.join(os.path.dirname(__file__), "template_maker.py")
spec = importlib.util.spec_from_file_location("template_maker", template_maker_path)
template_maker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template_maker)
create_template = template_maker.create_template

class EmailCreator:
    def __init__(self):
        """
        Initialize the EmailCreator with a template from the template maker.
        """
        # Call create_template with the required arguments
    
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
        # Generate the outreach template using the provided site_id
        self.outreach_template = create_template(
            gemini_personalized=True,
            variables={"site_id": site_id}
        )
        
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
    creator = EmailCreator(template)
    return creator.create_emails(urls)


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create an instance of EmailCreator with the default template
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
