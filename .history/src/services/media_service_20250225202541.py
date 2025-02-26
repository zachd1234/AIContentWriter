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
            1. For images, the mediaUrl must be the URL returned by GenerateImage
            2. For videos, the mediaUrl must be the YouTube URL returned by GetYouTubeVideo
            3. The insertBefore value must be an EXACT copy of text from the blog post
            4. Do NOT include any explanatory text, code blocks, or backticks
            5. Return ONLY the JSON array
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
                
                insert_before = placement['insertBefore']
                media_type = placement['mediaType']
                print(f"  Type: {media_type}")
                print(f"  Insert Before: {insert_before[:50]}...")
                
                # Debug: Check if text exists in content
                print(f"  Text exists in content: {insert_before in html_content}")
                print(f"  Content length before: {len(html_content)}")
                
                if media_type == 'image':
                    wordpress_url = placement['mediaUrl']
                    media_html = f'<img src="{wordpress_url}" alt="{placement.get("description", "")}" />'
                    print(f"  📸 Created image HTML with URL: {wordpress_url}")
                else:  # video
                    video_id = placement['mediaUrl'].split('watch?v=')[-1]
                    media_html = f'<iframe style="aspect-ratio: 16 / 9; width: 100%" src="https://www.youtube.com/embed/{video_id}" title="{placement.get("description", "")}" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen></iframe>'
                    print(f"  🎥 Created video HTML with ID: {video_id}")
                
                # Store the content before replacement
                content_before = html_content
                
                # Do the replacement
                html_content = html_content.replace(
                    insert_before, 
                    f"{media_html}\n{insert_before}"
                )
                
                # Debug: Check if replacement worked
                print(f"  Content length after: {len(html_content)}")
                print(f"  Content changed: {content_before != html_content}")
                
                if content_before == html_content:
                    print("  ⚠️ Warning: Content unchanged after replacement!")
                    # Additional debug: Print the exact characters around where we expect the match
                    pos = html_content.find(insert_before[:50])
                    if pos != -1:
                        print(f"  Context: ...{html_content[pos-20:pos+70]}...")
                else:
                    print("  ✅ Media inserted successfully")
            
            return html_content
            
        except Exception as e:
            print(f"Error in media population: {str(e)}")
            return html_content
def main():
   post_writer = PostWriterV2(base_url="https://ruckquest.com")
   sample_post = """<h1>How to Start Rucking: A Comprehensive Guide</h1>


<h2>What is Rucking?</h2>


<p>Rucking is simply <strong>walking with weight on your back</strong>.  It's a low-impact, full-body workout that combines cardiovascular exercise with strength training.  Unlike running, rucking is gentler on your joints, making it accessible to a wider range of fitness levels.  The added weight challenges your muscles, improving strength and endurance.  It's a versatile activity that can be done virtually anywhere – from city streets to hiking trails.</p>


<h2>Why Start Rucking?</h2>


<p>Rucking offers a multitude of benefits, making it a popular choice for fitness enthusiasts and those seeking a unique workout experience:</p>


<ul>
 <li><strong>Improved Cardiovascular Health:</strong> Rucking elevates your heart rate, improving cardiovascular fitness and reducing the risk of heart disease.</li>
 <li><strong>Increased Strength and Endurance:</strong> The added weight strengthens your legs, core, and back muscles, building both strength and endurance.</li>
 <li><strong>Calorie Burning:</strong> Rucking burns significantly more calories than regular walking, aiding in weight loss and management.</li>
 <li><strong>Enhanced Mental Well-being:</strong>  The outdoor nature of rucking and the potential for social interaction contribute to improved mental health and stress reduction.</li>
 <li><strong>Low Impact Exercise:</strong>  Unlike high-impact activities like running, rucking is easier on your joints, reducing the risk of injury.</li>
 <li><strong>Improved Posture:</strong>  The weight on your back encourages better posture and core engagement.</li>
</ul>




<h2>Getting Started: Your First Ruck</h2>


<h3>1. Choose Your Gear:</h3>


<ul>
 <li><strong>Ruckpack:</strong> Invest in a comfortable and durable ruckpack designed for carrying weight.  Avoid using a flimsy backpack; a dedicated ruckpack provides better weight distribution and support.</li>
 <li><strong>Weight:</strong> Start with a manageable weight, such as 10-25 pounds.  You can use readily available weights like dumbbells wrapped in a towel, or specialized ruck plates. Gradually increase the weight as you get stronger.  Never exceed 1/3 of your body weight.</li>
 <li><strong>Footwear:</strong> Wear comfortable and supportive shoes or boots suitable for walking or hiking.  Good traction is essential, especially on uneven terrain.</li>
 <li><strong>Clothing:</strong> Wear moisture-wicking clothing appropriate for the weather conditions.  Layers are recommended to adjust to changing temperatures.</li>
</ul>


<h3>2. Plan Your Route:</h3>


<p>Begin with short distances, such as 1-2 miles, on relatively flat terrain.  As you gain experience, you can gradually increase the distance and challenge yourself with more varied routes.</p>


<h3>3. Warm-up and Cool-down:</h3>


<p>Always warm up before starting your ruck with light cardio, such as a brisk walk or some dynamic stretches.  Cool down afterward with static stretches to improve flexibility and reduce muscle soreness.</p>


<h3>4. Pace Yourself:</h3>


<p>Maintain a comfortable pace.  Aim for a pace of 15-20 minutes per mile initially.  If you find yourself moving slower than 20 minutes per mile, reduce the weight.  Listen to your body and take breaks when needed.</p>


<h3>5. Stay Hydrated:</h3>


<p>Carry water with you, especially during longer rucks.  Dehydration can significantly impact your performance and well-being.</p>


<h3>6. Gradual Progression:</h3>


<p>Start with 1-2 rucking sessions per week.  Gradually increase the frequency, duration, distance, and weight as your fitness improves.  Avoid increasing any of these factors by more than 10% per week.</p>
"""


   enhanced_post = post_writer.populate_media_in_html(
       sample_post
   )
   print(f"Enhanced Post: {enhanced_post}")


if __name__ == "__main__":
   main()