import logging
import os
import sys
from typing import Dict, Any, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv
import traceback
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import tool

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
            model = GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
            
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

    def generate_advanced_personalized_email_agentic(self, url: str, site_id: int) -> str:
        """
        Generates a highly personalized email based on website analysis and database information
        using an agentic approach with LangChain.
        
        Args:
            url: The URL of the website to analyze
            site_id: The ID of the site in the database
            
        Returns:
            String containing the personalized email body
        """
        logger.info(f"Generating advanced personalized email (agentic) for URL: {url}, site_id: {site_id}")
        
        try:
            # First, analyze the website to understand its audience and value proposition
            website_analysis = self.analyze_website(url)
            logger.info(f"Website analysis completed, length: {len(website_analysis)} characters")
            
            # Get the blog info from the database
            blog_info = self.db_service.get_blog_info(site_id)
            if not blog_info:
                raise ValueError(f"No blog information found for site_id: {site_id}")
            
            blog_name = blog_info.get('blog_name') or blog_info.get('topic')
            blog_url = blog_info.get('url', '')
            blog_description = blog_info.get('description', '')
            
            # Print the blog info to verify
            print("\nBlog Information:")
            print(f"Blog Name: {blog_name}")
            print(f"Blog URL: {blog_url}")
            print(f"Blog Description: {blog_description}")
            
            logger.info(f"Retrieved blog name: {blog_name}, URL: {blog_url}")
            
            # Fetch one recent post from our blog to use as an example
            our_recent_post = self._fetch_recent_post(blog_url if blog_url else url)
            
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
            
            # Load environment variables
            load_dotenv()
            
            # Initialize Vertex AI
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
            if not project_id:
                project_id = os.getenv('GOOGLE_PROJECT_ID')
            
            if not project_id:
                raise ValueError("Google Cloud Project ID not found in environment variables")
            
            # Initialize Vertex AI properly
            vertexai.init(project=project_id, location="us-central1")
            
            # Create a new model instance using the experimental model for better creative thinking
            llm = ChatVertexAI(
                model_name="gemini-2.0-flash-thinking-exp-01-21",
                temperature=0.7,
                max_output_tokens=2048
            )
            
            # Define the tools for our agent
            
            # Tool 1: Generate Outreach Angle
            @tool
            def generate_outreach_angle(blog_name: str, blog_description: str, target_url: str, website_analysis: str) -> str:
                """
                Generates a strong outreach angle that connects our blog topic to the target website's audience.
                
                Args:
                    blog_name: The name of our blog
                    blog_description: Description of our blog
                    target_url: The URL of the target website
                    website_analysis: Analysis of the target website
                    
                Returns:
                    A concise 1-2 sentence outreach angle
                """
                prompt = f"""Act as an expert in content outreach strategy. Your task is to generate ONE strong outreach angle that connects our blog topic to the target website's audience in a **clear, simple, and compelling way**.

📌 **Given the following details:**
- **Our Blog:** {blog_name} - {blog_description}
- **Target Website:** {target_url} - {website_analysis}

🎯 **Your Goal:**  
- Identify the **most natural and compelling reason** why this target site's audience would care about our blog topic.  
- Look for **gaps in their content** (e.g., missing topics, outdated information, trends they haven't covered).  
- Keep it **simple, direct, and highly relevant to their audience**—avoid generic connections.  

📌 **Guidelines for Generating the Outreach Angle:**  
1️⃣ **Identify a missing angle or untapped topic** that would improve their site's content.  
2️⃣ **Frame it as an opportunity for their audience** (Why should their readers care?)  
3️⃣ **If relevant, use a trend, statistic, or unique positioning to justify it.**  

🔹 **Output Format:**  
✅ A **concise, 1-2 sentence outreach angle** (not a full email).  
✅ **No unnecessary explanations or fluff—keep it punchy, casual, and relevant.**  
✅ **Avoid sounding too formal or overly promotional.**  
"""
                
                # Use the same model for consistency
                angle_model = GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
                response = angle_model.generate_content(
                    prompt,
                    generation_config=GenerationConfig(
                        temperature=0.7
                    )
                )
                
                return response.text.strip()
            
            # Tool 2: Create Outreach Email
            @tool
            def create_outreach_email(
                outreach_angle: str, 
                blog_name: str, 
                blog_description: str, 
                target_url: str, 
                website_analysis: str,
                founder_name: str,
                blog_url: str,
                recent_work_url: str
            ) -> str:
                """
                Creates a personalized outreach email based on the outreach angle.
                
                Args:
                    outreach_angle: The outreach angle to use
                    blog_name: The name of our blog
                    blog_description: Description of our blog
                    target_url: The URL of the target website
                    website_analysis: Analysis of the target website
                    founder_name: Name of the founder
                    blog_url: URL of our blog
                    recent_work_url: URL of a recent post to showcase
                    
                Returns:
                    A fully structured outreach email
                """
                prompt = f"""Act as an expert in persuasive outreach and email writing. Your task is to generate a **concise, engaging, and highly personalized outreach pitch** based on the provided outreach angle.

📌 **Given the following details:**
- **Target Website:** {target_url} - {website_analysis}
- **Our Blog Post:** {blog_name} - {blog_description}
- **Outreach Angle:** {outreach_angle} 

🎯 **Your Goal:**
- Write a **compelling outreach pitch** that logically highlights why their website should feature our content.  
- Use **clear, direct reasoning** to connect their audience's needs to our blog topic.  
- Avoid sounding too generic, spammy, or overly promotional—keep it **natural and human-like**.  
- Keep the **call to action easy to respond to.**

📌 **Email Structure:**
1️⃣ **Logical Pitch** → Present the outreach angle as your core argument, explaining why it matters to their audience.
   - Identify a **gap in their content** (e.g., missing topics, outdated information, unexplored trends).  
   - Use the exact reasoning from the outreach angle, just phrased conversationally.  
   - Your tone should be **clever and insightful.**  
   - Use **data, trends, or specific audience problems** to strengthen the argument.  
   - Keep this to 2-3 sentences maximum.

2️⃣ **Introduction & Offer** → Briefly introduce our blog and offer a guest post.  
   - Example: *"I'm the founder of [Blog Name], and we'd love to write an educational guest post about [Outreach Angle Topic]."*  

3️⃣ **Call to Action (Low-Friction Ask)** → Ask if they'd be open to receiving topic ideas.  
   - Example: *"Let me know if this interests you, and I'll send over some topic ideas."* 

4️⃣ **Sign off** → Include a professional signature.
   - Format exactly as: "Best,\\n{founder_name}\\nFounder of {blog_name}\\n{blog_url}"

5️⃣ **P.S. Section (Credibility Boost)** → Link to a sample post for validation.  
   - Example: *"P.S. Here's a sample of a recent post we wrote about [Brief Topic]: {recent_work_url}"*  

🚨 **IMPORTANT Constraints:**  
- **DO NOT generate a subject line.**  
- **DO NOT generate a greeting (e.g., 'Hi [Name],').**  
- **DO NOT generate an introduction or compliment.** (That is handled separately.)  
- **ONLY generate the body of the email, beginning immediately with the logical pitch.**  
- **Return only text with no formatting.**
"""
                
                # Use the same model for consistency
                email_model = GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
                response = email_model.generate_content(
                    prompt,
                    generation_config=GenerationConfig(
                        temperature=0.7
                    )
                )
                
                return response.text.strip()
            
            # Create the agent with the tools
            tools = [generate_outreach_angle, create_outreach_email]
            
            # Create the agent executor
            agent = create_react_agent(llm, tools, REACT_CHAT_SYSTEM_PROMPT)
            agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
            
            # Run the agent
            result = agent_executor.invoke({
                "input": f"""Your task is to generate a personalized outreach email for a blog outreach campaign.

First, generate an outreach angle that connects our blog to the target website's audience.
Then, use that outreach angle to create a personalized outreach email.

Here's the information you need:
- Our Blog: {blog_name} - {blog_description}
- Target Website: {url} - {website_analysis}
- Founder Name: {founder_name}
- Blog URL: {blog_url}
- Recent Work URL: {recent_work_url}

Please follow these steps:
1. Call the generate_outreach_angle tool to create a compelling outreach angle
2. Call the create_outreach_email tool to craft the full email using that angle
3. Return the final email text
"""
            })
            
            # Extract the final email from the result
            outreach_email = result["output"]
            
            # Log the extracted text
            print(f"\nGenerated outreach email (agentic): {outreach_email}\n")
            logger.info(f"Generated outreach email (agentic): {outreach_email}")
            
            # Return the outreach email
            return outreach_email
                
        except Exception as e:
            logger.error(f"Error generating advanced personalized email (agentic): {str(e)}")
            print(f"Exception details: {str(e)}")
            traceback_str = traceback.format_exc()
            print(f"Traceback: {traceback_str}")
            return f"Error generating outreach email: {str(e)}"

    def generate_advanced_personalized_email(self, url: str, site_id: int) -> str:
        """
        Generates a highly personalized email based on website analysis and database information.
        
        Args:
            url: The URL of the website to analyze
            site_id: The ID of the site in the database
            
        Returns:
            String containing the personalized email body
        """
        logger.info(f"Generating advanced personalized email for URL: {url}, site_id: {site_id}")
        
        try:
            # First, analyze the website to understand its audience and value proposition
            website_analysis = self.analyze_website(url)
            logger.info(f"Website analysis completed, length: {len(website_analysis)} characters")
            
            # Get the blog info from the database
            blog_info = self.db_service.get_blog_info(site_id)
            if not blog_info:
                raise ValueError(f"No blog information found for site_id: {site_id}")
            
            blog_name = blog_info.get('blog_name') or blog_info.get('topic')
            blog_url = blog_info.get('url', '')
            blog_description = blog_info.get('description', '')
            
            # Print the blog info to verify
            print("\nBlog Information:")
            print(f"Blog Name: {blog_name}")
            print(f"Blog URL: {blog_url}")
            print(f"Blog Description: {blog_description}")
            
            logger.info(f"Retrieved blog name: {blog_name}, URL: {blog_url}")
            
            # Generate the outreach angle
            outreach_angle_prompt = f"""Act as an expert in content outreach strategy. Your task is to generate ONE strong outreach angle that connects our blog topic to the target website's audience in a **clear, simple, and compelling way**.

📌 **Given the following details:**
- **Our Blog:** {blog_name} - {blog_description}
- **Target Website:** {url} - {website_analysis}

🎯 **Your Goal:**  
- Identify the **most natural and compelling reason** why this target site's audience would care about our blog topic.  
- Look for **gaps in their content** (e.g., missing topics, outdated information, trends they haven't covered).  
- Keep it **simple, direct, and highly relevant to their audience**—avoid generic connections.  

📌 **Guidelines for Generating the Outreach Angle:**  
1️⃣ **Identify a missing angle or untapped topic** that would improve their site's content.  
2️⃣ **Frame it as an opportunity for their audience** (Why should their readers care?)  
3️⃣ **If relevant, use a trend, statistic, or unique positioning to justify it.**  

🔹 **Output Format:**  
✅ A **concise, 1-2 sentence outreach angle** (not a full email).  
✅ **No unnecessary explanations or fluff—keep it punchy, casual, and relevant.**  
✅ **Avoid sounding too formal or overly promotional.**  

🎯 **Example Outputs:**  
- **For a kids' fitness camp:** *"Rucking is a fun, team-based endurance activity that helps kids build strength and confidence. Since your camp emphasizes outdoor activity, adding rucking could provide a unique way for kids to stay active while learning resilience."*  
- **For a personal training site:** *"Rucking is a growing fitness trend that improves endurance and strength, yet it's missing from your blog. Adding it could introduce your audience to a simple yet powerful workout method that aligns with your fitness philosophy."*  
- **For a doctor's health blog:** *"Rucking is scientifically proven to improve longevity and cardiovascular health, yet it's rarely discussed in mainstream fitness. Since your blog focuses on holistic health, covering rucking as a sustainable fitness method could provide valuable insights to your readers."*  
"""

            # Load environment variables
            load_dotenv()
            
            # Initialize Vertex AI
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
            if not project_id:
                project_id = os.getenv('GOOGLE_PROJECT_ID')
            
            if not project_id:
                raise ValueError("Google Cloud Project ID not found in environment variables")
            
            # Initialize Vertex AI properly
            vertexai.init(project=project_id, location="us-central1")
            
            # Create a new model instance using the same model as ContentGenerator
            research_model = GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
            
            # Log the prompt for debugging
            print(f"\nSending prompt to Gemini API:\n{outreach_angle_prompt[:200]}...\n")
            
            # Make the API call exactly like in ContentGenerator.research_topic
            response = research_model.generate_content(
                outreach_angle_prompt,
                generation_config=GenerationConfig(
                    temperature=0.7
                )
            )
            
            # Log the raw response for debugging
            print(f"\nRaw response from Gemini API: {response}\n")
            
            # Extract the text from the response
            outreach_angle = response.text.strip()
            
            # Log the extracted text
            print(f"\nExtracted outreach angle: {outreach_angle}\n")
            logger.info(f"Generated outreach angle: {outreach_angle}")
            
            # Fetch one recent post from our blog to use as an example
            our_recent_post = self._fetch_recent_post(blog_url if blog_url else url)
            
            # Print the URL to verify we got it
            if our_recent_post:
                logger.info(f"Using this as our recent work URL: {our_recent_post}")
                recent_work_url = our_recent_post
            
            # Get the founder name from the database
            founder_name = self.db_service.get_founder_name(site_id)
            logger.info(f"Retrieved founder name: {founder_name}")
            
            # Generate the outreach pitch
            outreach_pitch_prompt = f"""Act as an expert in persuasive outreach and email writing. Your task is to generate a **concise, engaging, and highly personalized outreach pitch** based on the provided outreach angle.

📌 **Given the following details:**
- **Target Website:** {url} - {website_analysis}
- **Our Blog Post:** {blog_name} - {blog_description}
- **Outreach Angle:** {outreach_angle} 

🎯 **Your Goal:**
- Write a **compelling outreach pitch** that logically highlights why their website should feature our content.  
- Use **clear, direct reasoning** to connect their audience's needs to our blog topic.  
- Avoid sounding too generic, spammy, or overly promotional—keep it **natural and human-like**.  
- Keep the **call to action easy to respond to.**

📌 **Email Structure:**

1️⃣ **Logical Pitch** → Present the outreach angle as your core argument, explaining why it matters to their audience.
   - Identify a **gap in their content** (e.g., missing topics, outdated information, unexplored trends).  
   - Use the exact reasoning from the outreach angle, just phrased conversationally.  
   - Your tone should be **clever and insightful.**  
   - Example tone: *"I was digging through [Company Name]'s blog and found lots of educational content about X. However, I was surprised you haven't covered Y, which is rapidly growing in popularity. Your audience will achieve X and Y benefits from learning about this topic."*  
   - Use **data, trends, or specific audience problems** to strengthen the argument.  
   - Keep this to 2-3 sentences maximum.


2️⃣ **Introduction & Offer** → Briefly introduce our blog and offer a guest post.  
   - Example: *"I'm the founder of [Blog Name], and we'd love to write an educational guest post about [Outreach Angle Topic]."*  

3️⃣ **Call to Action (Low-Friction Ask)** → Ask if they'd be open to receiving topic ideas.  
   - Example: *"Let me know if this interests you, and I'll send over some topic ideas."* 

4️⃣ **Sign off** → Include a professional signature.
   - Format exactly as: "Best,\\n{founder_name}\\nFounder of {blog_name}\\n{blog_url}"

5️⃣ **P.S. Section (Credibility Boost)** → Link to a sample post for validation.  
   - Example: *"P.S. Here's a sample of a recent post we wrote about [Brief Topic]."*  

🔹 **Output Format:**  
✅ A **fully structured email** with a natural, persuasive tone.  
✅ **No unnecessary explanations or filler text.**  
✅ **Use a conversational, direct approach.**  

🚨 **IMPORTANT Constraints:**  
- **DO NOT generate a subject line.**  
- **DO NOT generate a greeting (e.g., 'Hi [Name],').**  
- **DO NOT generate an introduction or compliment.** (That is handled separately.)  
- **ONLY generate the body of the email, beginning immediately with the logical pitch.**  
- **Return only text with no formatting.**

IMPORTANT:
- Use the founder name: {founder_name}
- Use the blog name: {blog_name}
- Include this sample post URL: {recent_work_url}
- Make sure to incorporate the outreach angle naturally
- Follow the email structure. Do not include an introduction that was not part of the email structure. 
"""

            # Create a new model instance for the pitch
            pitch_model = GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
            
            # Log the prompt for debugging
            print(f"\nSending pitch prompt to Gemini API:\n{outreach_pitch_prompt[:200]}...\n")
            
            # Make the API call
            pitch_response = pitch_model.generate_content(
                outreach_pitch_prompt,
                generation_config=GenerationConfig(
                    temperature=0.7
                )
            )
            
            # Log the raw response for debugging
            print(f"\nRaw response from Gemini API: {pitch_response}\n")
            
            # Extract the text from the response
            outreach_pitch = pitch_response.text.strip()
            
            # Log the extracted text
            print(f"\nExtracted outreach pitch: {outreach_pitch}\n")
            logger.info(f"Generated outreach pitch: {outreach_pitch}")
            
            # Return the outreach pitch
            return outreach_pitch
                
        except Exception as e:
            logger.error(f"Error generating advanced personalized email: {str(e)}")
            print(f"Exception details: {str(e)}")
            traceback_str = traceback.format_exc()
            print(f"Traceback: {traceback_str}")
            return f"Error generating outreach pitch: {str(e)}"

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