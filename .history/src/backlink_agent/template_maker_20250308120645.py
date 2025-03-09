import logging
import os
import requests
from typing import Dict, Any, Optional
from xml.etree import ElementTree as ET
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv

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
        
        # Load environment variables
        load_dotenv()
        
        # Initialize Vertex AI
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        if project_id:
            try:
                vertexai.init(project=project_id, location="us-central1")
                self.model = GenerativeModel("gemini-1.5-flash-001")
                self.api_configured = True
                logger.info("Gemini API initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Gemini API: {str(e)}")
                self.api_configured = False
        else:
            logger.warning("GOOGLE_CLOUD_PROJECT_ID not found in environment variables")
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
            # Try to fetch the sitemap with proper headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            
            # Try different sitemap URLs
            sitemap_urls = [
                f"{site_url.rstrip('/')}/post-sitemap.xml",
                f"{site_url.rstrip('/')}/sitemap.xml",
                f"{site_url.rstrip('/')}/sitemap_index.xml",
                f"{site_url.rstrip('/')}/sitemap-posts.xml"
            ]
            
            for sitemap_url in sitemap_urls:
                logger.info(f"Trying sitemap: {sitemap_url}")
                try:
                    response = requests.get(sitemap_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    # Parse the XML
                    root = ET.fromstring(response.content)
                    
                    # Find the first valid post URL in the sitemap
                    for url in root.findall(".//{*}url"):
                        loc = url.find(".//{*}loc")
                        if loc is not None and loc.text and "/blog/" not in loc.text and not loc.text.endswith('/'):
                            logger.info(f"Found recent post: {loc.text}")
                            return loc.text
                    
                except Exception as e:
                    logger.warning(f"Error with sitemap {sitemap_url}: {str(e)}")
                    continue
            
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

Use this template structure, but personalize it based on their blog content:

My name is {variables.get('sender_name', '[Name]')} and I am the founder of {variables.get('blog_name', '[Blog Name]')}.

Your readers can benefit from [how their readers can benefit from this blog's content]. Here's a sample of my most recent work: {variables.get('recent_work_url', '[Recent work URL]')}

I wanted to see if we could talk about collaborating together via link exchange and/or contributing to a guest post on your site.

Let me know what you think.

Best,

{variables.get('sender_name', '[Name]')}

IMPORTANT: 
1. Keep the introduction exactly as "I am the founder of [blog name]"
2. Personalize ONLY the part about "how their readers can benefit" based on the blog's content
3. Keep all other parts of the template exactly as shown
4. Return only the email body, no subject line
"""

        if not self.api_configured:
            raise ValueError("Gemini API not configured. Set GOOGLE_CLOUD_PROJECT_ID environment variable.")
        
        try:
            # Generate the response using Vertex AI
            generation_config = GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=1024,
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Return the body
            body = response.text.strip()
            
            # Generate a subject line
            subject = f"Collaboration opportunity with {variables.get('sender_name', 'me')}"
            
            return {
                "subject": subject,
                "body": body
            }
                
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
    
    # Test the template maker
    template_maker = TemplateMaker()
    
    # Test Gemini personalized template
    variables = {
        "site_url": "https://ruckquest.com",
        "sender_name": "Alex Johnson",
        "blog_name": "Fitness Insights",
        "recent_work_url": "https://fitnessinsights.com/best-home-workouts-2023/"
    }
    
    try:
        template = template_maker.create_template("gemini_personalized", variables)
        
        print("Subject:", template["subject"])
        print("\nBody:")
        print(template["body"])
    except Exception as e:
        print(f"Error creating template: {str(e)}") 