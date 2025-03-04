import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
import google.generativeai as genai
from typing import Dict, List
import json
import requests
from api.serper_api import fetch_videos
from api.wordpress_media_api import WordPressMediaHandler
import re
from pydantic import BaseModel

class GetImgAIClient:
    def __init__(self, base_url: str):
        load_dotenv()
        self.API_KEY = os.getenv('GETIMG_API_KEY')
        self.API_URL = os.getenv('GETIMG_API_URL')
        self.GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
        self.base_url = base_url
        
        # Initialize Gemini for prompt enhancement
        self.llm = ChatGoogleGenerativeAI(
            model="models/gemini-2.0-flash-thinking-exp-01-21",
            temperature=0.7,
            google_api_key=os.getenv('GOOGLE_API_KEY')
        )
        
        # Update to use the new vision model
        self.vision_model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-thinking-exp-01-21",  # Updated model name
            temperature=0.1,
            google_api_key=self.GOOGLE_API_KEY
        )

    def enhance_prompt(self, basic_prompt: str) -> str:
        """Uses LLM to create a detailed image generation prompt."""
        prompt = f"""Create a highly detailed image generation prompt based on this concept: "{basic_prompt}"
        
        Include specific details about:
        - Composition and layout
        - Lighting and atmosphere
        - Colors and tone
        - Style and artistic approach
        - Important elements and their relationships
        - Mood and feeling
        
        Format as a single, detailed paragraph that flows naturally.
        Focus on visual elements that AI image generators excel at.
        Avoid technical or diagrammatic elements.
        """
        
        response = self.llm.invoke(prompt)
        return response.content


    def generate_image(self, prompt: str) -> str:
        """Generates an AI image and uploads it to WordPress."""
        try:
            print("original prompt: ", prompt)
            # Step 1: Enhance the prompt
            detailed_prompt = self.enhance_prompt(prompt)
            print("🔹 Enhanced prompt:", detailed_prompt)

            # Step 2: Generate image from GetImg
            data = {
                "prompt": detailed_prompt,
                "width": 1024,
                "height": 1024,
                "steps": 4,
                "output_format": "jpeg",
                "response_format": "url"
            }

            headers = {
                "Authorization": f"Bearer {self.API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            response = requests.post(self.API_URL, json=data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if "url" in result:
                    getimg_url = result["url"]  # This is the source image URL
                    print("✅ Generated image URL:", getimg_url)
                    
                    # Step 3: Upload to WordPress
                    try:
                        wp_handler = WordPressMediaHandler(
                            base_url=self.base_url,
                        )
                        media_id = wp_handler.upload_image_from_url(getimg_url)  # Use the GetImg URL
                        print(f"📤 Image uploaded to WordPress. Media ID: {media_id}")
                        return f"{media_id}"
                        
                    except Exception as wp_error:
                        print(f"❌ WordPress upload failed: {str(wp_error)}")
                        return getimg_url  # Return the GetImg URL as fallback

            return "❌ Image generation failed"

        except Exception as e:
            print(f"❌ Error in image generation process: {str(e)}")
            return f"Error generating image: {str(e)}"

    def getYouTubeVideo(self, vision: str) -> str:
        """
        Takes a high-level vision for a video and returns the best matching YouTube video.
        """
        try:
            # Step 1: Generate an optimized search query from the vision
            search_prompt = f"""Convert this video vision into a short YouTube search query:
            Vision: {vision}
            Create a search query that will find videos matching this vision.
            Return only 2-5 words that would work best as a YouTube search"""

            response = self.llm.invoke(search_prompt)
            search_query = response.content.strip()
            print("🔍 Generated search query:", search_query)
            
            # Step 2: Fetch video results
            videos = fetch_videos(search_query)
            print("\n📺 Fetched videos:", json.dumps(videos, indent=2))
            if not videos:
                print("❌ No videos found")
                return "No videos found"
                
            # Step 3: Select best matching video - IMPROVED PROMPT
            selection_prompt = f"""Given this vision for a video:
            '{vision}'
            
            Select the best matching video from these results:
            {json.dumps(videos, indent=2)}
            
            Consider:
            - How well it matches the vision
            - Video quality and professionalism
            - Educational value
            
            IMPORTANT: You must return ONLY the complete YouTube URL with no additional text.
            For example: https://www.youtube.com/watch?v=abcdef
            Do not include any explanations, just the URL."""
            
            print("\n🤔 Selecting best video...")
            response = self.llm.invoke(selection_prompt)
            print("Response: ", response.content, response)
            best_video_url = response.content.strip()
            print("✅ Selected video URL:", best_video_url)
            
            # Validate the URL format
            if not best_video_url.startswith("https://www.youtube.com/watch?v="):
                print("⚠️ Invalid URL format, selecting first video as fallback")
                # Fallback: use the first video if the response isn't a valid URL
                if videos and len(videos) > 0 and "link" in videos[0]:
                    best_video_url = videos[0]["link"]
                    print("✅ Using fallback video URL:", best_video_url)
            
            return best_video_url
            
        except Exception as e:
            print(f"❌ Error finding video: {str(e)}")
            return f"Error finding video: {str(e)}"

class PostWriterV2:
    def __init__(self, base_url=None):
        load_dotenv()
        
        # Set Google Application Credentials
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # Store the base_url for later use
        self.base_url = base_url
        
        # Initialize the LLM with Gemini configuration
        self.llm = ChatGoogleGenerativeAI(
            model="models/gemini-2.0-flash-thinking-exp-01-21",
            temperature=0.7,
            max_output_tokens=2048,
            google_api_key=os.getenv('GOOGLE_API_KEY')
        )
        
        # Initialize GetImgAIClient with base_url
        self.img_client = GetImgAIClient(base_url=base_url) if base_url else GetImgAIClient()
        
        # Create a closure that includes the base_url
        def generate_image_with_url(prompt: str) -> str:    
            return self.img_client.generate_image(prompt)
        
        # Define the image generation tool with the wrapped function
        generate_image_tool = Tool(
            name="GenerateImage",
            func=generate_image_with_url,
            description="""Creates AI-generated illustrations to help visualize concepts.
            Describe your vision for the image - what you want to see in the image like you are a director setting up the shot."""
        )
        
        get_youtube_video_tool = Tool(
            name="GetYouTubeVideo",
            func=self.img_client.getYouTubeVideo,
            description="""Gets best YouTube video based on vision.
            Describe to this tool your ideal YouTube video for this placement - what you want the video to show or explain to the reader."""
        )
        
        # Initialize the agent with both tools
        self.agent = initialize_agent(
            tools=[generate_image_tool, get_youtube_video_tool],
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,
            early_stopping_method="generate"
        )
        
        # Set up the system message
        self.system_message = """You are a professional blog post editor. Your task is to enhance blog posts with relevant images and videos, but ONLY when they meaningfully contribute to the reader's understanding or experience.
        IMPORTANT:
        - Return ONLY the JSON object, nothing else
        - The insertBefore value must be an exact copy of text from the blog post
        - Space out the media placements so that they are not all bunched up together
        - Limit media to 3 placements maximum"""
    
    def enhance_post(self, blog_post: str) -> str:
        """Enhances the blog post with media"""
        try:
            print("\n🔍 Starting post enhancement process...")
            print(f"Blog post length: {len(blog_post)} characters")
            
            # Skip first 200 words
            words = blog_post.split()
            if len(words) > 200:
                truncated_post = ' '.join(words[200:])
                print(f"Skipping first 200 words. New length: {len(truncated_post)} characters")
            else:
                truncated_post = blog_post
                print("Post shorter than 200 words, using full text")

            # Define the response schema for structured output
            response_schema = {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "insertBefore": {"type": "STRING"},
                        "mediaType": {
                            "type": "STRING",
                            "enum": ["image", "video"]
                        },
                        "mediaUrl": {"type": "STRING"},
                        "description": {"type": "STRING"}
                    },
                    "required": ["insertBefore", "mediaType", "mediaUrl", "description"]
                }
            }

            # Create the prompt for the agent with clearer instructions
            prompt = f"""
            {self.system_message}
            
            Here's the blog post to enhance:
            {truncated_post}

            INSTRUCTIONS FOR USING TOOLS:
            1. Read the blog post and identify 2-3 good places to add media between paragraphs
            2. For each place, decide whether an image or video would be most helpful
            3. Use the appropriate tool (GenerateImage or GetYouTubeVideo) to create that media            
            4. After using all tools, compile your results into a JSON array
            
            Each media placement MUST:
            - Directly help readers understand the content or provide valuable visual context
            - ONLY be placed BETWEEN complete HTML elements (paragraphs, sections, list items)
            - NEVER be placed within a paragraph, sentence, or HTML element
            - Make sense in the overall context of the post
                        
            IMPORTANT: When using tools, you MUST follow this EXACT format:
            
            Thought: I need to [describe your reasoning]
            Action: [tool name]
            Action Input: [tool input]

            Available tools:
            
            - GenerateImage
                Creates AI-generated illustrations to help visualize concepts
                * Best for: atmospheric scenes, conceptual illustrations, visual metaphors
                * CORRECT USAGE EXAMPLE:
                  Thought: I need an image showing proper rucking technique
                  Action: GenerateImage
                  Action Input: A person rucking through a forest trail with proper posture
            
            - GetYouTubeVideo
                Finds existing YouTube content
                * Best for: expert explanations, real demonstrations, educational content
                * CORRECT USAGE EXAMPLE:
                  Thought: I need a video demonstrating rucking technique
                  Action: GetYouTubeVideo
                  Action Input: Proper rucking technique demonstration

            FINAL OUTPUT FORMAT:
            After using the tools, return ONLY a JSON array with this EXACT format:
            [
              {{
                "insertBefore": "exact text from the blog post",
                "mediaType": "image",
                "mediaUrl": "https://example.com/image.jpg",
                "description": "explanation of how this helps"
              }},
              {{
                "insertBefore": "another exact text from the blog post",
                "mediaType": "video",
                "mediaUrl": "https://youtube.com/watch?v=abcdef",
                "description": "explanation of how this helps"
              }}
            ]

            IMPORTANT RULES FOR FINAL OUTPUT:
            1. For images, the mediaUrl must be the URL returned by GenerateImage
            2. For videos, the mediaUrl must be the YouTube URL returned by GetYouTubeVideo
            3. The "insertBefore" value must be an EXACT copy-paste from the blog post. Include all HTML tags exactly as they appear (<p>, </p>, etc. Include all whitespace and line breaks exactly
            6. Do NOT include any explanatory text, code blocks, or backticks
            7. Return ONLY the JSON array
            """

            # Configure genai with API key
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            
            # Create the model with structured output configuration
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-001",  # Updated model name
                generation_config={
                    "temperature": 0.1,
                }
            )
            
            # Generate structured response
            response = model.generate_content(
                contents=prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": response_schema
                }
            )
            
            # Get the structured output
            structured_output = response.text
            print(f"📋 Structured output: {structured_output[:200]}...")

            # Process each media suggestion
            media_items = json.loads(structured_output)
            processed_items = []
            
            for item in media_items:
                if item["mediaType"] == "image":
                    # Generate image using existing method
                    image_url = self.img_client.generate_image(item["description"])
                    if "wp-content/uploads" in image_url:
                        item["mediaUrl"] = image_url
                        processed_items.append(item)
                elif item["mediaType"] == "video":
                    # Get video using existing method
                    video_url = self.img_client.getYouTubeVideo(item["description"])
                    if "youtube.com" in video_url:
                        item["mediaUrl"] = video_url
                        processed_items.append(item)

            return json.dumps(processed_items, indent=2)
            
        except Exception as e:
            print(f"\n❌ Error in enhance_post: {str(e)}")
            return "[]"

    def populate_media_in_html(self, html_content: str, base_url: str = None) -> str:
        """
        Takes HTML content, enhances it with media, and returns the final HTML
        
        Args:
            html_content (str): The HTML content to enhance
            base_url (str, optional): The base URL for media. Defaults to None.
            
        Returns:
            str: The enhanced HTML content with media
        """
        try:
            print("\n🎨 Starting media population process...")
            
            # Get media suggestions
            media_json = self.enhance_post(html_content)
            print(f"\n📦 Received media JSON: {media_json}")
            
            media_placements = json.loads(media_json)
            print(f"\n🔢 Processing {len(media_placements)} media placements")
            
            # Insert media HTML at specified locations
            for i, placement in enumerate(media_placements, 1):
                print(f"\n🖼️ Processing placement {i}:")
                
                # Get the exact insertion point text
                insert_before = placement['insertBefore']
                media_type = placement['mediaType']
                
                print(f"  Type: {media_type}")
                print(f"  Original Insert Before: {insert_before[:50]}...")
                
                # Find the exact text in the content without normalizing
                start_pos = html_content.find(insert_before)
                
                if start_pos == -1:
                    print("  ⚠️ Exact match not found, trying to find the paragraph...")
                    # Try to find the paragraph by its first few words
                    words = insert_before.split()[:8]  # First 8 words should be unique enough
                    search_text = ' '.join(words)
                    start_pos = html_content.find(search_text)
                
                if start_pos != -1:
                    # Create the media HTML
                    if media_type == 'image':
                        wordpress_url = placement['mediaUrl']
                        media_html = f'<img src="{wordpress_url}" alt="{placement.get("description", "")}" />'
                    else:  # video
                        video_url = placement['mediaUrl']
                        media_html = f'[embed]{video_url}[/embed]'
                    
                    # Insert the media before the paragraph
                    html_content = html_content[:start_pos] + f"\n{media_html}\n\n" + html_content[start_pos:]
                    print("  ✅ Media inserted successfully")
                else:
                    print("  ❌ Could not find insertion point")
            
            return html_content
            
        except Exception as e:
            print(f"Error in media population: {str(e)}")
            return html_content
def main():
   post_writer = PostWriterV2(base_url="https://ruckquest.com")
   sample_post = """"Understanding Y Combinator’s Startup School
Y Combinator’s Startup School is an invaluable free educational program designed to support aspiring entrepreneurs on their journey from idea to launch. As one of the most renowned startup accelerators in the world, Y Combinator offers this initiative to democratize access to knowledge and resources that can help new ventures succeed.

The program provides a wealth of resources that cater to the diverse needs of budding founders, including:

Comprehensive Online Courses: These self-paced courses cover critical topics such as product development, market fit, fundraising, and scaling ventures.
Mentorship Opportunities: Participants can engage with experienced entrepreneurs and industry veterans who provide guidance and insights tailored to their specific challenges.
Peer Networking: Startup School fosters a collaborative environment where participants can connect with fellow aspiring entrepreneurs, creating opportunities for knowledge exchange and potential partnerships.
Through these resources, aspiring founders are positioned to navigate the complexities of establishing a startup more effectively. This network of support becomes increasingly important in fields like artificial intelligence, where technology evolves rapidly, and innovation is key.

For tech enthusiasts entering the AI sector, Startup School holds particular significance. As the landscape becomes more competitive and intricate, having access to mentorship and resources can make all the difference. The program not only equips participants with essential skills but also connects them with like-minded individuals who can inspire and motivate them to turn their innovative ideas into reality.

In summary, Y Combinator’s Startup School is an indispensable platform for any aspiring entrepreneur, especially those looking to make their mark in technology and AI. By providing essential resources, mentorship, and networking opportunities, the program empowers individuals to transform their visions into successful startups.

Key Features of Startup School
Startup School offers a unique platform designed to cater to the needs of budding entrepreneurs. One of the standout features is the access to a community of like-minded startups and experienced mentors. This vibrant network not only fosters collaboration but also encourages the sharing of ideas and experiences. By engaging with fellow founders, participants can gain valuable insights, share challenges, and celebrate successes together. The support from seasoned mentors adds another layer of guidance, as they provide actionable feedback and wisdom drawn from their own entrepreneurial journeys.

In addition to community engagement, Startup School boasts a detailed curriculum covering essential startup strategies. This comprehensive program is particularly beneficial for those navigating the complexities of launching and scaling a business. Notably, the curriculum includes AI-specific sessions, which delve into how artificial intelligence can be leveraged to enhance business operations and drive innovation. These sessions are designed not just to teach theoretical concepts, but to provide participants with practical skills and strategies they can implement in real-world scenarios.

Together, these key features of Startup School create an enriching environment where entrepreneurs can thrive, learn, and transform their ideas into successful ventures.

Preparing for the Journey: Key Steps to Launching an AI Startup
Launching an AI startup can seem like a daunting task, but breaking it down into key, manageable steps can pave the way for success. Here are some essential actions to take as you prepare for your entrepreneurial journey in the AI space:

1. Identifying a Unique Problem in the AI Space to Solve

The first step is to pinpoint a specific pain point or gap in the market that your AI technology can address. This requires a mix of creativity and critical thinking. Consider industries ripe for innovation, such as healthcare, finance, or logistics. Engage with potential users to understand their challenges and frustrations. By identifying a unique problem, you can carve out a niche for your startup and ensure that your solution has a clear purpose.

2. Conducting Thorough Market Research and Validation

Once you’ve established a potential problem to solve, the next step is to conduct comprehensive market research. This involves analyzing existing solutions, identifying competitors, and understanding market dynamics. Utilize surveys, interviews, and focus groups to gather insights from your target audience. Additionally, look into trends and predictions in the AI sector to validate your idea. This research will not only help you refine your solution but also gauge the demand for it, setting a solid foundation for your startup.

3. Developing a Minimum Viable Product (MVP) and Iterating Based on Feedback

With a validated idea in hand, you can now focus on developing a Minimum Viable Product (MVP). An MVP allows you to create a functional version of your solution with just enough features to attract early users and gather valuable feedback. The goal here is to test your assumptions and learn what works and what doesn’t in real-world applications. Implement feedback loops where users can easily share their experiences and suggestions. Use this data to iterate and improve your product, ensuring that it meets the evolving needs of your audience.

By following these three key steps—identifying a unique problem, conducting market research, and developing an MVP—you’ll be well on your way to building a successful AI startup. Each step builds upon the previous one, creating a robust framework that can adapt as you grow and learn throughout your entrepreneurial journey.

Building a Strong Foundation
A solid foundation is crucial for any venture aiming for long-term success. This involves not just assembling resources but also honing in on the people and strategies that will drive your business forward. Here are key components to consider in this foundational phase:

Assembling a Skilled and Complementary Team: The first step in building a strong foundation is to gather a team of individuals whose skills complement one another. It’s vital to identify team members who bring diverse expertise to the table, paving the way for effective collaboration. A well-rounded team should include experts in areas such as marketing, operations, finance, and product development. By leveraging each person’s unique strengths, you can create a balanced group that can tackle challenges from multiple angles. Additionally, fostering a culture of open communication and mutual respect ensures that everyone feels valued, which can significantly enhance teamwork.
Transitioning from team composition, we move on to the next critical element that ties the team’s capabilities to practical outcomes.

Creating a Strategic Business Plan and Financial Model: Once you have your talented team in place, the next step is to formulate a comprehensive strategic business plan. This document serves as a roadmap, outlining your business’s vision, mission, and objectives, while detailing the strategies to achieve them. Moreover, incorporating a robust financial model is essential to ascertain the viability of your plans. This model should project your revenue streams, anticipated expenses, cash flow, and profitability. By regularly updating your financial projections, you can remain agile and responsive to any changes in the market environment.
Together, assembling a skilled team and creating a strategic business plan with a solid financial model lays a robust framework for sustainable growth. By investing time and effort in these foundational elements, you position your venture for success in the competitive landscape.
"""


   enhanced_post = post_writer.populate_media_in_html(
       sample_post
   )
   print(f"Enhanced Post: {enhanced_post}")


if __name__ == "__main__":
   main()