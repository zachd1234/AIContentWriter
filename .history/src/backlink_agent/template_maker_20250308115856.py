import logging
import requests
from typing import Dict, Any, Optional
from xml.etree import ElementTree as ET
import google.generativeai as genai

logger = logging.getLogger(__name__)

class TemplateMaker:
    """
    Class responsible for creating email templates for outreach campaigns.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TemplateMaker with Gemini API.
        
        Args:
            api_key: API key for Google's Gemini API
        """
        logger.info("Initializing TemplateMaker with Gemini")
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
    
    def _fetch_recent_post(self, site_url: str) -> Optional[str]:
        """
        Fetch a recent post URL from the site's sitemap.
        
        Args:
            site_url: The website URL to fetch a recent post from
            
        Returns:
            A URL of a recent post or None if unable to fetch
        """
        try:
            # Try to fetch the sitemap
            sitemap_url = f"{site_url.rstrip('/')}/post-sitemap.xml"
            logger.info(f"Fetching sitemap from: {sitemap_url}")
            
            response = requests.get(sitemap_url, timeout=10)
            response.raise_for_status()
            
            # Parse the XML
            root = ET.fromstring(response.content)
            
            # Find the first valid post URL in the sitemap
            for url in root.findall(".//{*}url"):
                loc = url.find(".//{*}loc")
                if loc is not None and loc.text and "/blog/" not in loc.text and not loc.text.endswith('/'):
                    logger.info(f"Found recent post: {loc.text}")
                    return loc.text
            
            logger.warning(f"No valid posts found in sitemap for {site_url}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching recent post from {site_url}: {str(e)}")
            return None
    
    def _generate_personalized_email(self, site_url: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        Use Gemini to generate a personalized email based on the site and template variables.
        
        Args:
            site_url: The target website URL
            variables: Dictionary of variables to customize the template
            
        Returns:
            Dictionary containing the generated subject and body
        """
        # Fetch one recent post to provide context
        recent_post = self._fetch_recent_post(site_url)
        recent_post_text = recent_post if recent_post else "No recent post found"
        
        # Create prompt for Gemini
        prompt = f"""
You are a professional outreach specialist. Create a personalized email to the owner of the blog at {site_url}.
I've found this recent post from their site:
{recent_post_text}

Use this template as a guide, but make it specific to their blog content:
---
My name is {variables.get('sender_name', '[Name]')} and {variables.get('sender_leverage_point', '[Your unique leverage point]')}.

Your readers can benefit from [how their readers can benefit from this blog's content]. Here's a sample of my most recent work: {variables.get('recent_work_url', '[Recent work URL]')}

I wanted to see if we could talk about collaborating together via link exchange and/or contributing to a guest post on your site.

Let me know what you think.

Best,
{variables.get('sender_name', '[Name]')}
---

Make the email sound natural, friendly, and personalized to their specific blog content. Don't use generic phrases.
Return only the email subject and body, formatted as:
SUBJECT: [Your subject line]
BODY:
[Your email body]
"""

        try:
            # Call the Gemini API
            if not self.api_key:
                raise ValueError("No API key provided for Gemini")
            
            # Configure the model
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            # Initialize the model
            model = genai.GenerativeModel(
                model_name="gemini-pro",
                generation_config=generation_config
            )
            
            # Generate the response
            response = model.generate_content(prompt)
            
            # Parse the response
            content = response.text.strip()
            
            # Extract subject and body
            if "SUBJECT:" in content and "BODY:" in content:
                subject = content.split("SUBJECT:")[1].split("BODY:")[0].strip()
                body = content.split("BODY:")[1].strip()
                
                return {
                    "subject": subject,
                    "body": body
                }
            else:
                raise ValueError("Gemini response not in expected format")
                
        except Exception as e:
            logger.error(f"Error generating personalized email with Gemini: {str(e)}")
            raise
    
    def create_template(self, template_type: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an email template based on the specified type and variables.
        
        Args:
            template_type: The type of template to create (currently only supports "gemini_personalized")
            variables: Optional dictionary of variables to customize the template
            
        Returns:
            Dictionary containing the template subject and body
        """
        logger.info(f"Creating template of type: {template_type}")
        
        if variables is None:
            variables = {}
        
        # For Gemini-personalized template
        if template_type == "gemini_personalized":
            if "site_url" not in variables:
                raise ValueError("No site_url provided for Gemini personalized template")
            
            return self._generate_personalized_email(variables["site_url"], variables)
        else:
            raise ValueError(f"Unsupported template type: {template_type}")


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the template maker with Gemini personalization
    # Replace with your actual API key
    template_maker = TemplateMaker(api_key="your_gemini_api_key_here")
    
    # Test Gemini personalized template
    variables = {
        "site_url": "https://ruckquest.com",
        "sender_name": "Alex Johnson",
        "sender_company": "Fitness Insights",
        "sender_leverage_point": "I write for a fitness blog with over 100k monthly visitors",
        "recent_work_url": "https://fitnessinsights.com/best-home-workouts-2023/"
    }
    
    try:
        template = template_maker.create_template("gemini_personalized", variables)
        
        print("Subject:", template["subject"])
        print("\nBody:")
        print(template["body"])
    except Exception as e:
        print(f"Error creating template: {str(e)}") 