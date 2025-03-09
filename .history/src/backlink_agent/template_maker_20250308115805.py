import logging
import requests
import random
from typing import Dict, Any, Optional, List
from xml.etree import ElementTree as ET
import openai  # or another LLM client library

logger = logging.getLogger(__name__)

class TemplateMaker:
    """
    Class responsible for creating email templates for outreach campaigns.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TemplateMaker.
        
        Args:
            api_key: API key for the LLM service (e.g., OpenAI)
        """
        logger.info("Initializing TemplateMaker")
        self.api_key = api_key
        if api_key:
            openai.api_key = api_key
    
    def _fetch_recent_posts(self, site_url: str, limit: int = 3) -> List[str]:
        """
        Fetch recent post URLs from the site's sitemap.
        
        Args:
            site_url: The website URL to fetch recent posts from
            limit: Maximum number of posts to return
            
        Returns:
            A list of URLs of recent posts
        """
        try:
            # Try to fetch the sitemap
            sitemap_url = f"{site_url.rstrip('/')}/post-sitemap.xml"
            logger.info(f"Fetching sitemap from: {sitemap_url}")
            
            response = requests.get(sitemap_url, timeout=10)
            response.raise_for_status()
            
            # Parse the XML
            root = ET.fromstring(response.content)
            
            # Find all URLs in the sitemap
            urls = []
            for url in root.findall(".//{*}url"):
                loc = url.find(".//{*}loc")
                if loc is not None and loc.text and "/blog/" not in loc.text and not loc.text.endswith('/'):
                    urls.append(loc.text)
            
            # Return a few recent post URLs
            if urls:
                return urls[:limit]
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching recent posts from {site_url}: {str(e)}")
            return []
    
    def _generate_personalized_email(self, site_url: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        Use an LLM to generate a personalized email based on the site and template variables.
        
        Args:
            site_url: The target website URL
            variables: Dictionary of variables to customize the template
            
        Returns:
            Dictionary containing the generated subject and body
        """
        # Fetch recent posts to provide context to the LLM
        recent_posts = self._fetch_recent_posts(site_url)
        recent_posts_text = "\n".join(recent_posts) if recent_posts else "No recent posts found"
        
        # Create prompt for the LLM
        prompt = f"""
You are a professional outreach specialist. Create a personalized email to the owner of the blog at {site_url}.
I've found these recent posts from their site:
{recent_posts_text}

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
            # Call the LLM API
            if not self.api_key:
                logger.warning("No API key provided for LLM. Using template instead.")
                return self._fallback_template(variables)
            
            response = openai.ChatCompletion.create(
                model="gpt-4",  # or another appropriate model
                messages=[
                    {"role": "system", "content": "You are a professional outreach specialist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse the response
            content = response.choices[0].message.content.strip()
            
            # Extract subject and body
            if "SUBJECT:" in content and "BODY:" in content:
                subject = content.split("SUBJECT:")[1].split("BODY:")[0].strip()
                body = content.split("BODY:")[1].strip()
                
                return {
                    "subject": subject,
                    "body": body
                }
            else:
                logger.warning("LLM response not in expected format. Using fallback template.")
                return self._fallback_template(variables)
                
        except Exception as e:
            logger.error(f"Error generating personalized email with LLM: {str(e)}")
            return self._fallback_template(variables)
    
    def _fallback_template(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        Create a fallback template when LLM generation fails.
        
        Args:
            variables: Dictionary of variables to customize the template
            
        Returns:
            Dictionary containing the template subject and body
        """
        subject = f"Collaboration opportunity with {variables.get('sender_company', 'our team')}"
        
        body = f"""
Hello,

My name is {variables.get('sender_name', '[Name]')} and {variables.get('sender_leverage_point', '[Your unique leverage point]')}.

Your readers can benefit from {variables.get('reader_benefit', 'our content')}. Here's a sample of my most recent work: {variables.get('recent_work_url', '[Recent work URL]')}

I wanted to see if we could talk about collaborating together via link exchange and/or contributing to a guest post on your site.

Let me know what you think.

Best,
{variables.get('sender_name', '[Name]')}
        """
        
        return {
            "subject": subject,
            "body": body.strip()
        }
    
    def create_template(self, template_type: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an email template based on the specified type and variables.
        
        Args:
            template_type: The type of template to create (e.g., "backlink_request", "guest_post", "llm_personalized")
            variables: Optional dictionary of variables to customize the template
            
        Returns:
            Dictionary containing the template subject and body
        """
        logger.info(f"Creating template of type: {template_type}")
        
        if variables is None:
            variables = {}
        
        # For LLM-personalized template
        if template_type == "llm_personalized":
            if "site_url" not in variables:
                logger.warning("No site_url provided for LLM personalized template")
                return self._fallback_template(variables)
            
            return self._generate_personalized_email(variables["site_url"], variables)
            
        # Default template parts
        subject = ""
        body = ""
        
        # Select template based on type
        if template_type == "backlink_request":
            subject = "Opportunity to collaborate with {site_name}"
            body = """
Hello {recipient_name},

I recently came across your article on {article_title} and found it very insightful.

I noticed you mentioned {topic} in your post. I've actually published a comprehensive guide on this topic that might complement your article well: {our_article_url}

Would you consider adding a link to our resource in your article? I believe it would provide additional value to your readers.

Thank you for considering my request. I look forward to potentially collaborating with you.

Best regards,
{sender_name}
{sender_company}
            """
            
        elif template_type == "guest_post":
            subject = "Guest post proposal for {site_name}"
            body = """
Hello {recipient_name},

I'm {sender_name} from {sender_company}, and I'm reaching out because I'm a regular reader of {site_name}.

I particularly enjoyed your recent article about {article_title}. The insights on {topic} were particularly valuable.

I'd like to contribute a guest post to your site on a related topic. Here are a few ideas that might interest your audience:

1. {idea_1}
2. {idea_2}
3. {idea_3}

Let me know if any of these resonate with you, or if you have other topics you'd prefer me to cover.

Thanks for your time and consideration.

Best regards,
{sender_name}
{sender_company}
            """
            
        else:
            logger.warning(f"Unknown template type: {template_type}")
            return self._fallback_template(variables)
        
        # Replace variables in template
        for key, value in variables.items():
            subject = subject.replace("{" + key + "}", str(value))
            body = body.replace("{" + key + "}", str(value))
        
        return {
            "subject": subject,
            "body": body.strip()
        }


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the template maker with LLM personalization
    # Replace with your actual API key
    template_maker = TemplateMaker(api_key="your_openai_api_key_here")
    
    # Test LLM personalized template
    variables = {
        "site_url": "https://ruckquest.com",
        "sender_name": "Alex Johnson",
        "sender_company": "Fitness Insights",
        "sender_leverage_point": "I write for a fitness blog with over 100k monthly visitors",
        "reader_benefit": "our extensive collection of workout guides and fitness equipment reviews",
        "recent_work_url": "https://fitnessinsights.com/best-home-workouts-2023/"
    }
    
    template = template_maker.create_template("llm_personalized", variables)
    
    print("Subject:", template["subject"])
    print("\nBody:")
    print(template["body"]) 