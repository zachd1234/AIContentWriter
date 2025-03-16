import requests
import logging
from typing import List, Dict, Any, Optional
import os
import sys
import time
import traceback

# Get the absolute path to the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the project root to Python's path if it's not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import using the absolute path
from src.backlink_agent import template_maker

logger = logging.getLogger(__name__)

# Hard-coded API URL
POST_PITCH_API_URL = "https://post-pitch-fork.onrender.com/"

class EmailCreator:
    def __init__(self):
        """
        Initialize the EmailCreator.
        """
        # We'll set the template in create_emails
        self.outreach_template = None
    
    def _get_post_pitch(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Call the post pitch API for a single URL with retry logic for 502 errors.
        """
        max_retries = 3
        retry_delay = 10  # seconds
        
        for attempt in range(max_retries):
            try:
                api_endpoint = f"{POST_PITCH_API_URL.rstrip('/')}/email_data_lenient?url={url}"
                
                print(f"Calling post pitch API (attempt {attempt+1}/{max_retries}): {api_endpoint}")
                
                # Use curl-like headers
                headers = {
                    'User-Agent': 'curl/7.68.0',
                    'Accept': '*/*'
                }
                
                start_time = time.time()
                response = requests.get(
                    api_endpoint,
                    headers=headers,
                    timeout=120
                )
                elapsed_time = time.time() - start_time
                
                print(f"Response received in {elapsed_time:.2f} seconds. Status: {response.status_code}")
                
                # If we get a 502, the service might be warming up
                if response.status_code == 502:
                    if attempt < max_retries - 1:
                        print(f"Got 502 error, service might be warming up. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.RequestException as e:
                print(f"Error calling post pitch API for {url}: {str(e)}")
                
                # Only retry on 502 errors
                if "502 Server Error" in str(e) and attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Error getting post pitch for {url}: {str(e)}")
                    return None
        
        print(f"All {max_retries} attempts failed for URL: {url}")
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
        self.outreach_template = template_maker_instance.create_advanced(site_id)
        
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

    def create_advanced_email(self, url: str, site_id: int) -> Optional[Dict[str, str]]:
        """
        Create a single advanced personalized email for a target website.
        
        Args:
            url: Target website URL
            site_id: Integer ID of the site to use for template generation
            
        Returns:
            Email object with subject, body, and recipient email, or None if failed
        """
        logger.info(f"Creating advanced personalized email for URL: {url}, site_id: {site_id}")
        
        try:
            # Create an instance of TemplateMaker and call its advanced email generation method
            template_maker_instance = template_maker.TemplateMaker()
            advanced_personalization = template_maker_instance.generate_advanced_personalized_email(url, site_id)
            
            # Get pitch data from the post pitch API
            pitch_data = self._get_post_pitch(url)
            
            if not pitch_data or "error" in pitch_data:
                logger.warning(f"Failed to get pitch data for {url}")
                return None
            
            # Extract necessary information from pitch_data
            subject = pitch_data.get("subject", "")
            post_pitch_personalization = pitch_data.get("body", "")
            recipient_email = pitch_data.get("email", "")
            
            # Skip if any required field is missing
            if not all([subject, post_pitch_personalization, recipient_email, advanced_personalization]):
                logger.warning(f"Missing required data for {url}")
                return None
            
            # Combine post pitch personalization with the advanced personalization
            full_body = f"{post_pitch_personalization}\n{advanced_personalization}"
            
            email = {
                "subject": subject,
                "body": full_body,
                "email": recipient_email
            }
            
            logger.info(f"Successfully created advanced email for {url}")
            return email
            
        except Exception as e:
            logger.error(f"Error creating advanced email for {url}: {str(e)}")
            traceback_str = traceback.format_exc()
            logger.error(f"Traceback: {traceback_str}")
            return None


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
