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
            model="gemini-pro",
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
        """Enhances the blog post with AI-generated images"""
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
            - Be placed BETWEEN paragraphs or sections, never within them
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
            2. For images, the mediaUrl must be the URL returned by GenerateImage
            3. For videos, the mediaUrl must be the YouTube URL returned by GetYouTubeVideo
            4. Do NOT include any explanatory text, code blocks, or backticks
            5. Return ONLY the JSON array
            """
            
            print("\n🤖 Invoking agent...")
            response = self.agent.invoke({"input": prompt})
            print(f"\n📝 Raw agent response: {response}")
            
            if not response:
                print("❌ No response from agent")
                return "[]"
            
            output_text = response.get("output", "")
            print(f"\n🔍 Parsing output: {output_text[:200]}...")  # First 200 chars
            
            try:
                # Validate the JSON format
                return self.validate_json_response(output_text)
                
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON parsing error: {str(e)}")
                print(f"Problematic text: {output_text}")
                return "[]"
            
        except Exception as e:
            print(f"\n❌ Error in enhance_post: {str(e)}")
            return "[]"

    def validate_json_response(self, agent_output: str) -> str:
        """Validates the JSON format using Gemini's structured output capabilities"""
        try:
            print(f"\n🔍 Raw agent output (first 200 chars): {agent_output[:200]}...")
            
            # Configure genai with API key
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            
            # Create the model with structured output configuration
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config={
                    "temperature": 0.1,
                }
            )
            
            # Generate structured response
            response = model.generate_content(
                contents=agent_output,
                generation_config={
                    "response_mime_type": "application/json"
                }
            )
            
            # Get the structured output
            structured_output = response.text
            print(f"📋 Structured output: {structured_output[:200]}...")
            
            # Parse the JSON
            try:
                media_items = json.loads(structured_output)
                print(f"✅ Successfully parsed structured JSON with {len(media_items)} items")
            except json.JSONDecodeError as e:
                print(f"❌ Structured JSON parsing error: {str(e)}")
                return "[]"
            
            # Validate each media item
            valid_media = []
            for item in media_items:
                # Check required fields
                if not all(key in item for key in ["insertBefore", "mediaType", "mediaUrl", "description"]):
                    print("❌ Missing required fields in media item")
                    continue
                
                media_url = item["mediaUrl"]
                media_type = item["mediaType"]
                
                # Validate based on media type
                is_valid = False
                if media_type == "image":
                    # For images: WordPress URL 
                    is_valid = "wp-content/uploads" in media_url
                elif media_type == "video":
                    # For videos: must be YouTube URL
                    is_valid = "youtube.com" in media_url
                
                if is_valid:
                    valid_media.append(item)
                    print(f"✅ Valid media: {media_type} - {media_url[:50]}...")
                else:
                    print(f"❌ Invalid media URL: {media_url[:50]}...")
            
            return json.dumps(valid_media, indent=2)
            
        except Exception as e:
            print(f"❌ Error validating JSON: {str(e)}")
            import traceback
            traceback.print_exc()
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
                
                insert_before = placement['insertBefore']
                media_type = placement['mediaType']
                print(f"  Type: {media_type}")
                print(f"  Insert Before: {insert_before[:50]}...")
                
                if media_type == 'image':
                    wordpress_url = placement['mediaUrl']
                    media_html = f'<img src="{wordpress_url}" alt="{placement.get("description", "")}" />'
                    print(f"  📸 Created image HTML with URL: {wordpress_url}")
                else:  # video
                    video_id = placement['mediaUrl'].split('watch?v=')[-1]
                    media_html = f'<iframe style="aspect-ratio: 16 / 9; width: 100%" src="https://www.youtube.com/embed/{video_id}" title="{placement.get("description", "")}" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen></iframe>'
                    print(f"  🎥 Created video HTML with ID: {video_id}")
                
                # Insert the media HTML
                html_content = html_content.replace(
                    insert_before, 
                    f"{media_html}\n{insert_before}"
                )
                print("  ✅ Media inserted successfully")
            
            return html_content
            
        except Exception as e:
            print(f"Error in media population: {str(e)}")
            return html_content

def main():
    test_json = """[
      {
        "insertBefore": "Getting Started: Your First Ruck",
        "mediaType": "image",
        "mediaUrl": "https://ruckquest.com/wp-content/uploads/2025/02/forest-hike-backpacking-nature-trail-man-1740462469509.jpg",
        "description": "This image shows proper rucking technique, which can help prevent injury and improve performance."
      },
      {
        "insertBefore": "2. Plan Your Route",
        "mediaType": "video",
        "mediaUrl": "https://www.youtube.com/watch?v=Dk07AiKLSOE",
        "description": "This video shows how to plan a rucking route, including how to choose the right terrain and distance."
      },
      {
        "insertBefore": "6. Gradual Progression",
        "mediaType": "video",
        "mediaUrl": "https://www.youtube.com/watch?v=0NqQBaLWaWw",
        "description": "This video demonstrates proper rucking form, which is essential for preventing injury and maximizing the benefits of rucking."
      }
    ]"""
    
    post_writer = PostWriterV2(base_url="https://ruckquest.com")
    validated_json = post_writer.validate_json_response(test_json)
    print("\nValidated JSON output:")
    print(validated_json)


if __name__ == "__main__":
    main() 