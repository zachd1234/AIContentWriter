import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class EmailCreator:
    def __init__(self, post_pitch_api_url: str, outreach_template: str):
        """
        Initialize the EmailCreator with the API URL and outreach template.
        
        Args:
            post_pitch_api_url: URL for the post pitch API
            outreach_template: Static template to append to each personalized message
        """
        self.post_pitch_api_url = post_pitch_api_url
        self.outreach_template = outreach_template
    
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
            api_endpoint = f"{self.post_pitch_api_url}email_data_lenient?url={url}"
            
            response = requests.get(
                api_endpoint,
                timeout=60  # Increased timeout as this API might take longer
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error getting post pitch for {url}: {str(e)}")
            return None
    
    def create_emails(self, urls: List[str]) -> List[Dict[str, str]]:
        """
        Create personalized emails for a list of URLs.
        
        Args:
            urls: List of target website URLs
            
        Returns:
            List of email objects with subject, body, and recipient email
        """
        emails = []
        
        for url in urls:
            pitch_data = self._get_post_pitch(url)
            
            if not pitch_data or "error" in pitch_data:
                logger.warning(f"Failed to get pitch data for {url}")
                continue
            
            # Extract necessary information from pitch_data
            try:
                subject = pitch_data.get("subject", "")
                personalization = pitch_data.get("personalization", "")
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
def create_outreach_emails(urls: List[str], api_url: str, template: str) -> List[Dict[str, str]]:
    """
    Convenience function to create outreach emails.
    
    Args:
        urls: List of target website URLs
        api_url: URL for the post pitch API
        template: Static template to append to each personalized message
        
    Returns:
        List of email objects with subject, body, and recipient email
    """
    creator = EmailCreator(api_url, template)
    return creator.create_emails(urls)
