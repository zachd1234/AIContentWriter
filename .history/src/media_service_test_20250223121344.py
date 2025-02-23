import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from typing import Dict
import json
import requests
from api.serper_api import fetch_videos
from api.wordpress_media_api import WordPressMediaHandler
import re

class GetImgAIClient:
    def __init__(self):
        load_dotenv()
        self.API_KEY = os.getenv('GETIMG_API_KEY')
        self.API_URL = os.getenv('GETIMG_API_URL')
        self.GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
        
        # Initialize Gemini for prompt enhancement
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
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


    def generate_image(self, prompt: str, base_url: str, width=1024, height=1024, steps=4) -> str:
        """Generates an AI image and uploads it to WordPress."""
        try:
            print("original prompt: ", prompt)
            # Step 1: Enhance the prompt
            detailed_prompt = self.enhance_prompt(prompt)
            print("🔹 Enhanced prompt:", detailed_prompt)

            # Step 2: Generate image
            data = {
                "prompt": detailed_prompt,
                "width": width,
                "height": height,
                "steps": steps,
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
                    image_url = result["url"]
                    print("✅ Generated image URL:", image_url)
                    
                    # Step 3: Upload to WordPress
                    try:
                        wp_handler = WordPressMediaHandler(
                            base_url=base_url,
                        )
                        media_id = wp_handler.upload_image_from_url(image_url)
                        print(f"📤 Image uploaded to WordPress. Media ID: {media_id}")
                        return f"{media_id}"
                        
                    except Exception as wp_error:
                        print(f"❌ WordPress upload failed: {str(wp_error)}")
                        return image_url

            return "❌ Image generation failed"

        except Exception as e:
            print(f"❌ Error in image generation process: {str(e)}")
            return f"Error generating image: {str(e)}"

    def getYouTubeVideo(self, vision: str) -> str:
        """
        Takes a high-level vision for a video and returns the best matching YouTube video.
        
        Args:
            vision (str): Description of what the ideal video should show/explain
            
        Returns:
            str: URL of the best matching YouTube video
        """
        try:
            # Step 1: Generate an optimized search query from the vision
            search_prompt = f"""Convert this video vision into a focused YouTube search query:
            Vision: {vision}
            Create a search query that will find videos matching this vision.
            Return only the search query, nothing else."""
            
            response = self.llm.invoke(search_prompt)
            search_query = response.content.strip()
            print("🔍 Generated search query:", search_query)
            
            # Step 2: Fetch video results
            videos = fetch_videos(search_query)
            if not videos:
                return "No videos found"
                
            # Step 3: Select best matching video
            selection_prompt = f"""Given this vision for a video:
            '{vision}'
            
            Select the best matching video from these results:
            {videos}
            
            Consider:
            - How well it matches the vision
            - Video quality and professionalism
            - Educational value
            
            Return ONLY the YouTube URL of the best video."""
            
            response = self.llm.invoke(selection_prompt)
            best_video_url = response.content.strip()
            print("✅ Selected video URL:", best_video_url)
            
            return best_video_url
            
        except Exception as e:
            print(f"❌ Error finding video: {str(e)}")
            return f"Error finding video: {str(e)}"

class PostWriterV2:
    def __init__(self):
        load_dotenv()
        
        # Set Google Application Credentials
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # Initialize the LLM with Gemini configuration
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            max_output_tokens=2048,
            google_api_key=os.getenv('GOOGLE_API_KEY')
        )
        
        self.img_client = GetImgAIClient()
        
        # Create a closure that includes the base_url
        def generate_image_with_url(prompt: str, base_url: str) -> str:
            return self.img_client.generate_image(prompt, base_url=base_url)
        
        # Define the image generation tool with the wrapped function
        generate_image_tool = Tool(
            name="GenerateImage",
            func=generate_image_with_url,
            description="""Creates AI-generated illustrations to help visualize concepts.
            Describe your vision for the image - what you want to see in the image like you are a director setting up the shot."""
        )
        
        fetch_videos_tool = Tool(
            name="FetchVideos",
            func=fetch_videos,
            description="Searches for relevant videos based on a query. Returns a list of video information including titles and URLs."
        )
        
        # Initialize the agent with both tools
        self.agent = initialize_agent(
            tools=[generate_image_tool, fetch_videos_tool],
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
        - Limit media to 3 placements maximum
        - Do Not add media to the beginning of the post"""

    def enhance_post(self, blog_post: str) -> str:
        """Enhances the blog post with AI-generated images"""
        try:
            # Create the prompt for the agent
            prompt = f"""
            {self.system_message}
            
            Here's the blog post to enhance:
            {blog_post}
            
            First, scan the content for natural break points between paragraphs or sections. For each potential location, evaluate:
            - Will this media actually help readers better understand the content?
            - Will this media provide valuable visual context or demonstration?
            - Is this placement between paragraphs or sections? 

            For each location you identify:
            1. Envision what would best help readers understand the content at this point. 

            You have these tools available:
            
            - GenerateImage
              Creates AI-generated illustrations to help visualize concepts
                * Best for: atmospheric scenes, conceptual illustrations, visual metaphors
                * Best when: abstract concepts need visualization
                * Not suitable for: technical diagrams, real-world documentation, precise details
            
            - FetchVideos
              Finds existing YouTube content
                * Will find the best video on YouTube that matches the vision
                * Best for: expert explanations, real demonstrations, educational content 

            For each chosen location, use the appropriate tool to create media that best matches your vision. 
            If no tool can adequately fulfill the vision, skip this placement.

            Return your suggestions as a JSON array where each object contains:
            - 'insertBefore': the exact text where media should be inserted
            - 'mediaType': either 'image' or 'video'
            - 'mediaUrl': the URL from either GenerateImage or FetchVideos
            - 'description': a specific explanation of how this media enhances understanding
            """
            
            # Run the agent
            response = self.agent.invoke({"input": prompt})
            
            # Extract JSON from the agent's response
            if not response:
                print("No response from agent")
                return "[]"
            
            output_text = response.get("output", "")
            
            # First try: direct JSON parsing
            try:
                if output_text.strip().startswith('['):
                    return output_text.strip()
            except:
                pass
            
            # Second try: find JSON array in text
            try:
                json_matches = re.findall(r'\[[\s\S]*?\]', output_text)
                if json_matches:
                    for json_str in json_matches:
                        if json.loads(json_str):  # Validate JSON
                            return json_str
            except:
                pass
            
            # If all parsing fails, return empty array
            print("Could not parse valid JSON from response:", output_text[:100])
            return "[]"

        except Exception as e:
            print(f"Error enhancing post: {str(e)}")
            return "[]"

    def populate_media_in_html(self, html_content: str, base_url: str) -> str:
        """
        Takes HTML content, enhances it with media, and returns the final HTML
        
        Args:
            html_content (str): The HTML content to enhance
            base_url (str): The base URL for WordPress media uploads
        """
        try:
            # Get media suggestions from enhance_post
            media_json = self.enhance_post(html_content)
            media_placements = json.loads(media_json)
            
            # Insert media HTML at specified locations
            for placement in media_placements:
                insert_before = placement['insertBefore']
                media_type = placement['mediaType']
                
                if media_type == 'image':
                    # Create WordPress handler with dynamic base_url
                    wp_handler = WordPressMediaHandler(base_url=base_url)
                    
                    # Generate and upload the image, getting back the WordPress URL
                    wordpress_url = wp_handler.upload_image_from_url(placement['mediaUrl'])
                    media_html = f'<p><img src="{wordpress_url}" alt="{placement.get("description", "")}" /></p>'
                else:  # video
                    # Extract video ID from YouTube URL
                    video_id = placement['mediaUrl'].split('watch?v=')[-1]
                    # Format video with proper iframe structure
                    media_html = f'<p><iframe style="aspect-ratio: 16 / 9; width: 100%" src="https://www.youtube.com/embed/{video_id}" title="{placement.get("description", "")}" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen></iframe></p>'
                
                # Insert the media HTML before the specified text
                html_content = html_content.replace(
                    insert_before, 
                    f"{media_html}\n{insert_before}"
                )
            
            return html_content
            
        except Exception as e:
            print(f"Error populating media: {str(e)}")
            return html_content

def main():
    # Initialize the client
    client = GetImgAIClient()
    
    # Test the image generation
    test_prompt = "A scientist conducting an environmental site assessment, wearing safety gear and taking soil samples"
    test_base_url = "https://ruckquest.com"
    
    try:
        result = client.generate_image(
            prompt=test_prompt,
            base_url=test_base_url
        )
        print("\n=== Test Results ===")
        print(f"Prompt: {test_prompt}")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")

    # Test the YouTube video fetching
    test_vision = "A comprehensive guide showing how to properly conduct an environmental site assessment, including soil sampling techniques and safety protocols"
    
    try:
        print("\n=== Testing YouTube Video Fetch ===")
        print(f"Vision: {test_vision}")
        video_url = client.getYouTubeVideo(test_vision)
        print(f"Selected Video URL: {video_url}")
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    main() 