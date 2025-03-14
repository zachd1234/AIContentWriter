import logging
import os
import requests
from typing import Dict, Any, Optional
from xml.etree import ElementTree as ET
import google.generativeai as genai

logger = logging.getLogger(__name__)

class TemplateMaker:
    """
    Class responsible for creating email templates for outreach campaigns.
    """
    
    def __init__(self):
        """
        Initialize the TemplateMaker with Gemini API from environment variables.
        """
        logger.info("Initializing TemplateMaker with Gemini")
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.api_configured = True
        else:
            logger.warning("GEMINI_API_KEY not found in environment variables")
            self.api_configured = False
    
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
    
    def _generate_personalized_content(self, site_url: str, variables: Dict[str, Any]) -> str:
        """
        Use Gemini to generate just the personalized content part of an email.
        
        Args:
            site_url: The target website URL
            variables: Dictionary of variables to customize the content
            
        Returns:
            The generated personalized content
        """
        # Fetch one recent post to provide context
        recent_post = self._fetch_recent_post(site_url)
        recent_post_text = recent_post if recent_post else "No recent post found"
        
        # Create prompt for Gemini - focusing only on the personalized content part
        prompt = f"""
You are a professional outreach specialist. Create ONLY the personalized content part of an email to the owner of the blog at {site_url}.
I've found this recent post from their site:
{recent_post_text}

I need ONLY the middle part of an email that explains how their readers can benefit from my content. 
The introduction and greeting will be handled separately.

Focus on creating 1-2 sentences that specifically mention:
1. How their readers can benefit from my content based on their blog's focus
2. Make it specific to their blog content and audience

Example format of what I need:
"Your readers interested in [specific topic from their blog] would find value in our [specific content type] that covers [specific benefit]. Our approach to [relevant topic] complements your content on [specific aspect from their blog]."

Keep it concise, natural, and highly personalized to their specific blog content. Don't use generic phrases.
Return ONLY the personalized content paragraph, nothing else.
"""

        if not self.api_configured:
            raise ValueError("Gemini API not configured. Set GEMINI_API_KEY environment variable.")
        
        try:
            # Configure the model
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 512,
            }
            
            # Initialize the model
            model = genai.GenerativeModel(
                model_name="gemini-pro",
                generation_config=generation_config
            )
            
            # Generate the response
            response = model.generate_content(prompt)
            
            # Return just the content
            return response.text.strip()
                
        except Exception as e:
            logger.error(f"Error generating personalized content with Gemini: {str(e)}")
            raise
    
    def create_template(self, template_type: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an email template based on the specified type and variables.
        
        Args:
            template_type: The type of template to create (currently only supports "gemini_personalized")
            variables: Optional dictionary of variables to customize the template
            
        Returns:
            Dictionary containing the template parts
        """
        logger.info(f"Creating template of type: {template_type}")
        
        if variables is None:
            variables = {}
        
        # For Gemini-personalized template
        if template_type == "gemini_personalized":
            if "site_url" not in variables:
                raise ValueError("No site_url provided for Gemini personalized template")
            
            # Generate just the personalized content
            personalized_content = self._generate_personalized_content(variables["site_url"], variables)
            
            # Construct the full email with standard parts
            subject = f"Collaboration opportunity with {variables.get('sender_company', 'our team')}"
            
            # The body will be assembled by the caller, we just return the personalized content
            return {
                "subject": subject,
                "personalized_content": personalized_content
            }
        else:
            raise ValueError(f"Unsupported template type: {template_type}")


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the template maker
    template_maker = TemplateMaker()
    
    # Test Gemini personalized template
    variables = {
        "site_url": "https://ruckquest.com",
        "sender_company": "Fitness Insights"
    }
    
    try:
        template_parts = template_maker.create_template("gemini_personalized", variables)
        
        print("Subject:", template_parts["subject"])
        print("\nPersonalized Content:")
        print(template_parts["personalized_content"])
        
        # Example of how the caller might assemble the full email
        sender_name = "Alex Johnson"
        sender_leverage_point = "I write for a fitness blog with over 100k monthly visitors"
        recent_work_url = "https://fitnessinsights.com/best-home-workouts-2023/"
        
        full_email = f"""
My name is {sender_name} and {sender_leverage_point}.

{template_parts["personalized_content"]} Here's a sample of my most recent work: {recent_work_url}

I wanted to see if we could talk about collaborating together via link exchange and/or contributing to a guest post on your site.

Let me know what you think.

Best,
{sender_name}
"""
        print("\nFull Email Example:")
        print(full_email)
        
    except Exception as e:
        print(f"Error creating template: {str(e)}") 