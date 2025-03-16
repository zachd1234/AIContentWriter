import logging
import os
import sys
from typing import Dict, Any, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv

# Add the parent directory to sys.path to import the sitemap_api module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.sitemap_api import fetch_posts_from_sitemap
from database_service import DatabaseService

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
        project_id = os.getenv('GOOGLE_PROJECT_ID')
        if project_id:
            try:
                # The GOOGLE_APPLICATION_CREDENTIALS env var is automatically used by the SDK
                vertexai.init(project=project_id, location="us-central1")
                self.model = GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
                self.api_configured = True
                logger.info("Gemini API initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Gemini API: {str(e)}")
                self.api_configured = False
        else:
            logger.warning("GOOGLE_PROJECT_ID not found in environment variables")
            self.api_configured = False
        
        # Initialize database service
        try:
            self.db_service = DatabaseService()
            logger.info("Database service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database service: {str(e)}")
            raise
    
    def _fetch_recent_post(self, site_url: str) -> Optional[str]:
        """
        Fetch a recent post URL from the site's sitemap using the sitemap_api module.
        
        Args:
            site_url: The website URL to fetch a recent post from
            
        Returns:
            A URL of a recent post or None if unable to fetch
        """
        try:
            # Use the existing sitemap_api to fetch posts
            posts = fetch_posts_from_sitemap(site_url)
            
            if posts and len(posts) > 0:
                # Filter out /blog/ URLs which are typically index pages, not actual posts
                for post in posts:
                    url = post['loc']
                    # Skip URLs that end with /blog/ or are just the blog index
                    if not url.endswith('/blog/') and not url.endswith('/blog'):
                        logger.info(f"Found recent post: {url}")
                        return url
                
                # If we didn't find any valid posts, use the first one as fallback
                logger.warning(f"No valid posts found, using first URL: {posts[0]['loc']}")
                return posts[0]['loc']
            else:
                logger.warning(f"No posts found for {site_url}")
                return None
            
        except Exception as e:
            logger.error(f"Error fetching recent post from {site_url}: {str(e)}")
            return None
    
    def _generate_personalized_email(self, site_url: str, variables: Dict[str, Any]) -> str:
        """
        Use Gemini to generate a personalized email based on the site and template variables.
        
        Args:
            site_url: The target website URL
            variables: Dictionary of variables to customize the template
            
        Returns:
            String containing the generated email body
        """
        # Get the site ID from variables
        site_id = variables.get('site_id')
        
        # Get the blog info from the database
        blog_info = self.db_service.get_blog_info(site_id)
        blog_name = blog_info.get('blog_name') or blog_info.get('topic')
        blog_url = blog_info.get('url', '')
        blog_description = blog_info.get('description', '')
        
        # Print the blog info to verify
        print("\nBlog Information:")
        print(f"Blog Name: {blog_name}")
        print(f"Blog URL: {blog_url}")
        print(f"Blog Description: {blog_description}")
        
        logger.info(f"Retrieved blog name: {blog_name}, URL: {blog_url}")
        
        # Fetch one recent post from the target site to provide context for the AI
        target_recent_post = self._fetch_recent_post(site_url)
        target_recent_post_text = target_recent_post if target_recent_post else "No recent post found"
        
        # Fetch our own recent post to use as an example of our work
        our_recent_post = self._fetch_recent_post(blog_url if blog_url else site_url)
        
        # Print the URL to verify we got it
        if our_recent_post:
            logger.info(f"Using this as our recent work URL: {our_recent_post}")
            recent_work_url = our_recent_post
        else:
            recent_work_url = "https://example.com/sample-post"  # Fallback URL
            logger.warning(f"No recent post found, using fallback URL: {recent_work_url}")
        
        # Get the founder name from the database
        founder_name = self.db_service.get_founder_name(site_id)
        logger.info(f"Retrieved founder name: {founder_name}")
        
        # Create prompt for Gemini
        prompt = f"""
You are a professional outreach specialist. Create a personalized email to the owner of the blog at {site_url}.

I've found this recent post from their site:
{target_recent_post_text}

About my blog:
Name: {blog_name}
Description: {blog_description}

Use this template structure, but personalize it based on their blog content:

My name is {founder_name} and I am the founder of {blog_name}.

Your readers can benefit from [how their readers can benefit from this blog's content]. Here's a sample of my most recent work: {recent_work_url}

I wanted to see if we could talk about collaborating together via link exchange and/or contributing to a guest post on your site.

Let me know what you think.

Best,

{founder_name}

IMPORTANT: 
1. Keep the introduction exactly as "I am the founder of {blog_name}"
2. Personalize ONLY the part about "how their readers can benefit" based on the blog's content
3. Keep all other parts of the template exactly as shown
4. Return only the email body, no subject line
"""

        if not self.api_configured:
            raise ValueError("Gemini API not configured. Set GOOGLE_PROJECT_ID environment variable.")
        
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
            
            # Return just the body text
            return response.text.strip()
                
        except Exception as e:
            logger.error(f"Error generating personalized email with Gemini: {str(e)}")
            raise
    
    def create_template(self, site_id: int) -> str:
        """
        Create a personalized email template for the specified site ID.
        
        Args:
            site_id: The ID of the site to use for template generation
            
        Returns:
            String containing the personalized email template
        """
        logger.info(f"Creating personalized template for site ID: {site_id}")
        
        # Get the blog info from the database
        blog_info = self.db_service.get_blog_info(site_id)
        
        if not blog_info:
            raise ValueError(f"No blog information found for site_id: {site_id}")
        
        site_url = blog_info.get('url')
        if not site_url:
            raise ValueError(f"No URL found for site_id: {site_id}")
        
        # Create variables dictionary with site_id
        variables = {"site_id": site_id}
        
        # Generate the personalized email
        return self._generate_personalized_email(site_url, variables)

    def analyze_website(self, url: str) -> str:
        """
        Scrapes a website and uses Gemini to analyze its content for outreach purposes.
        
        Args:
            url: The URL of the website to analyze
            
        Returns:
            String containing the analysis of the website's target audience, value proposition,
            and additional relevant facts
        """
        logger.info(f"Analyzing website: {url}")
        
        # Import the scrape_webpage function
        from api.serper_api import scrape_webpage
        
        # Scrape the webpage
        try:
            # Add http:// prefix if missing
            if not url.startswith('http'):
                url = 'https://' + url
                logger.info(f"Added https:// prefix, new URL: {url}")
            
            webpage_content = scrape_webpage(url)
            logger.info(f"Scraped content length: {len(str(webpage_content)) if webpage_content else 0} characters")
            
            if not webpage_content or webpage_content.startswith("Error"):
                logger.error(f"Failed to scrape content from {url}: {webpage_content}")
                return f"Unable to analyze website: {webpage_content}"
            
            # Create prompt for Gemini
            prompt = f"""Analyze the following website homepage text and extract key details to help craft a personalized outreach pitch. Answer these questions concisely:

1️⃣ Target Audience: Who is this website's main audience? Be specific (e.g., fitness enthusiasts, parents of young athletes, corporate professionals).

2️⃣ Value Proposition: What does this website offer its visitors? Summarize its core goal/service in 1-2 sentences.

3️⃣ Additional Relevant Facts: Identify any unique details about the website that could be useful when crafting a pitch for a collaboration. These should be specific insights about the website's structure, blog categories, mission, or content style that could influence how we approach outreach.

Website Content:
{webpage_content}"""

            # Initialize Vertex AI with the same model as ContentGenerator
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
            if not project_id:
                project_id = os.getenv('GOOGLE_PROJECT_ID')
            
            if not project_id:
                raise ValueError("Google Cloud Project ID not found in environment variables")
            
            # Re-initialize the model for each request to avoid any state issues
            vertexai.init(project=project_id, location="us-central1")
            model = GenerativeModel("gemini-1.5-flash-002")
            
            try:
                # Generate the response using the same approach as ContentGenerator
                response = model.generate_content(
                    prompt,
                    generation_config=GenerationConfig(
                        temperature=0.2,
                        max_output_tokens=1024,
                    )
                )
                
                # Return the analysis
                return response.text
                    
            except Exception as e:
                logger.error(f"Error analyzing website with Gemini: {str(e)}")
                raise
                
        except Exception as e:
            logger.error(f"Error in website analysis: {str(e)}")
            return f"Unable to analyze website: {str(e)}"

    def generate_advanced_personalized_email(self, url: str, site_id: int) -> str:
        """
        Generates a highly personalized email based on website analysis and database information.
        
        Args:
            url: The target website URL
            site_id: The ID of the site in the database
            
        Returns:
            String containing the personalized email body
        """
        logger.info(f"Generating advanced personalized email for URL: {url}, site_id: {site_id}")
        
        try:
            # First, analyze the website to understand its audience and value proposition
            website_analysis = self.analyze_website(url)
            blog_info = self.db_service.get_blog_info(site_id)


            return ""
                
        except Exception as e:
            logger.error(f"Error generating advanced personalized email: {str(e)}")
            raise

if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the template maker
    template_maker = TemplateMaker()
    
    # Test URLs for website analysis
    test_urls = [
        "partneresi.com",
        "https://emeranmayer.com/",
        "https://www.yourhousefitness.com/",
        "hotgroundgym.com"
    ]
    
    # Test website analysis for each URL
    for url in test_urls:
        print(f"\n{'='*80}")
        print(f"generating advanced personalized email for website: {url}")
        print(f"{'='*80}")
        
        try:
            analysis = template_maker.generate_advanced_personalized_email(url, 1)
            print(analysis)
        except Exception as e:
            print(f"Error analyzing website {url}: {str(e)}")
    
    # Uncomment to test the template creation
    """
    # Test Gemini personalized template
    site_id = 1  # Using site_id of 1
    
    try:
        body = template_maker.create_template(site_id)
        
        print("\nGenerated Email Body:")
        print(body)
    except Exception as e:
        print(f"Error creating template: {str(e)}")
    """ 