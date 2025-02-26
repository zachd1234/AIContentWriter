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
            model="models/gemini-1.5-pro",  # Updated with full model path
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
            model="models/gemini-1.5-pro",  # Updated with full model path
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
        """Validates the JSON format using a StrictJSON-inspired approach"""
        try:
            print(f"\n🔍 Raw agent output (first 200 chars): {agent_output[:200]}...")
            
            # Define our expected schema (similar to StrictJSON output_format)
            expected_format = {
                "type": "Array of media items with required type field",
                "items": [
                    {
                        "type": "Type of media (youtube, image, etc.)",
                        "videoId": "YouTube video ID (for youtube type)",
                        "prompt": "Image description (for image type)",
                        "position": "Position in the document (start, middle, end)",
                        "caption": "Caption for the media",
                        "url": "URL for the media"
                    }
                ]
            }
            
            # Step 1: Extract JSON from various formats
            cleaned_output = agent_output
            import re
            
            # Handle "Thought:Thought:" pattern (seen in logs)
            thought_thought_match = re.search(r'Thought:Thought:.*?(\[\s*\{.*?\}\s*\])', cleaned_output, re.DOTALL)
            if thought_thought_match:
                print(f"🔍 Detected JSON after Thought:Thought: pattern")
                cleaned_output = thought_thought_match.group(1).strip()
                print(f"✅ Successfully extracted JSON after Thought:Thought: pattern")
            
            # Handle Thought: blocks with JSON (common in agent outputs)
            elif "Thought:" in cleaned_output:
                print(f"🔍 Detected Thought: block")
                # Look for JSON array after Thought:
                thought_json_match = re.search(r'Thought:.*?(\[\s*\{.*?\}\s*\])', cleaned_output, re.DOTALL)
                if thought_json_match:
                    print(f"✅ Found JSON array after Thought:")
                    cleaned_output = thought_json_match.group(1).strip()
                else:
                    # Look for JSON in code blocks within Thought:
                    thought_code_match = re.search(r'Thought:.*?```+(?:json)?\s*([\s\S]*?)\s*```', cleaned_output, re.DOTALL)
                    if thought_code_match:
                        print(f"✅ Found JSON in code block after Thought:")
                        cleaned_output = thought_code_match.group(1).strip()
            
            # Handle both three and four backtick code blocks
            elif "````json" in cleaned_output or "```json" in cleaned_output:
                print(f"🔍 Detected JSON in code block format")
                # Replace four backticks with three for consistency
                cleaned_output = cleaned_output.replace("````json", "```json")
                # Extract content between ```json and ``` markers
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', cleaned_output)
                if json_match:
                    cleaned_output = json_match.group(1).strip()
                    print(f"✅ Successfully extracted JSON from code block")
            
            # Handle Final Answer: prefix
            elif "Final Answer:" in cleaned_output:
                print(f"🔍 Detected Final Answer: prefix")
                final_answer_match = re.search(r'Final Answer:\s*([\s\S]*)', cleaned_output)
                if final_answer_match:
                    cleaned_output = final_answer_match.group(1).strip()
                    print(f"✅ Successfully extracted content after Final Answer:")
            
            # Step 2: Clean up the output
            cleaned_output = cleaned_output.strip('`').strip()
            
            # Step 3: Try to parse the JSON with multiple fallback strategies
            try:
                # Direct parsing
                media_items = json.loads(cleaned_output)
                print(f"✅ Successfully parsed JSON directly")
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {str(e)}")
                
                # Try to find a JSON array in the text as a fallback
                json_array_match = re.search(r'\[\s*{.*}\s*\]', cleaned_output, re.DOTALL)
                if json_array_match:
                    json_str = json_array_match.group(0)
                    print(f"📋 Found JSON array: {json_str[:100]}...")
                    try:
                        media_items = json.loads(json_str)
                        print(f"✅ Successfully parsed JSON array")
                    except json.JSONDecodeError as e2:
                        print(f"❌ JSON array parsing error: {str(e2)}")
                        return "[]"
                else:
                    print("❌ Could not find valid JSON structure")
                    return "[]"
            
            # Step 4: Validate and normalize the media items (similar to StrictJSON type forcing)
            if not isinstance(media_items, list):
                if isinstance(media_items, dict):
                    # Single item returned as a dict
                    media_items = [media_items]
                else:
                    print(f"❌ Expected a list of media items, got {type(media_items)}")
                    return "[]"
            
            normalized_items = []
            for item in media_items:
                if not isinstance(item, dict):
                    print(f"❌ Expected a dict for media item, got {type(item)}")
                    continue
                    
                # Create a normalized item with required fields
                normalized_item = {}
                
                # Handle the insertBefore field if present
                if "insertBefore" in item:
                    print(f"✅ Found insertBefore field, mapping to position:start")
                    normalized_item["position"] = "start"
                
                # Determine the type (required field)
                if "type" in item:
                    media_type = item["type"].lower()
                    normalized_item["type"] = media_type
                elif "mediaType" in item:
                    media_type = item["mediaType"].lower()
                    normalized_item["type"] = media_type
                else:
                    print(f"❌ Missing required field 'type' in item: {item}")
                    continue
                    
                # Normalize type values
                if normalized_item["type"] in ["youtube", "video"]:
                    normalized_item["type"] = "youtube"
                    
                    # Get video ID (required for youtube)
                    if "videoId" in item:
                        normalized_item["videoId"] = item["videoId"]
                    elif "mediaUrl" in item:
                        # Extract video ID from URL
                        url = item["mediaUrl"]
                        video_id = None
                        
                        if "youtube.com/watch?v=" in url:
                            video_id = url.split("youtube.com/watch?v=")[1].split("&")[0]
                        elif "youtu.be/" in url:
                            video_id = url.split("youtu.be/")[1].split("?")[0]
                        
                        if video_id:
                            normalized_item["videoId"] = video_id
                        else:
                            print(f"❌ Could not extract videoId from URL: {url}")
                            continue
                    else:
                        print(f"❌ Missing required field 'videoId' for youtube item: {item}")
                    continue
                    
                elif normalized_item["type"] == "image":
                    # Get prompt (required for image)
                    if "prompt" in item:
                        normalized_item["prompt"] = item["prompt"]
                    elif "description" in item:
                        normalized_item["prompt"] = item["description"]
                    else:
                        print(f"❌ Missing required field 'prompt' for image item: {item}")
                        continue
                    
                    # Copy URL if available
                    if "url" in item:
                        normalized_item["url"] = item["url"]
                    elif "mediaUrl" in item:
                        normalized_item["url"] = item["mediaUrl"]
                else:
                    print(f"❌ Unsupported media type: {normalized_item['type']}")
                    continue
                
                # Copy optional fields
                if "position" not in normalized_item and "position" in item:
                    normalized_item["position"] = item["position"]
                elif "position" not in normalized_item:
                    normalized_item["position"] = "end"  # Default position
                    
                if "caption" in item:
                    normalized_item["caption"] = item["caption"]
                
                normalized_items.append(normalized_item)
            
            print(f"✅ Normalized to {len(normalized_items)} valid items")
            return json.dumps(normalized_items, indent=2)
        
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
                
                # Get position and determine where to insert
                position = placement.get('position', 'end')
                media_type = placement.get('type', '')
                print(f"  Type: {media_type}")
                
                # Find the insertion point based on position
                if position == 'start':
                    # Look for the first heading tag to insert before
                    import re
                    heading_match = re.search(r'<h[1-6][^>]*>.*?</h[1-6]>', html_content, re.DOTALL)
                    if heading_match:
                        insert_before = heading_match.group(0)
                        print(f"  Insert Before: {insert_before[:50]}...")
                    else:
                        # Default to beginning of content
                        insert_before = html_content.lstrip()
                        print(f"  Insert at beginning of content")
                else:
                    # Default to end - find a good paragraph to insert after
                    paragraphs = re.findall(r'<p[^>]*>.*?</p>', html_content, re.DOTALL)
                    if paragraphs and len(paragraphs) > 2:
                        # Insert before the third-to-last paragraph if available
                        insert_index = max(0, len(paragraphs) - 3)
                        insert_before = paragraphs[insert_index]
                        print(f"  Insert Before: {insert_before[:50]}...")
                    else:
                        # Default to end of content
                        insert_before = "</body>" if "</body>" in html_content else html_content
                        print(f"  Insert at end of content")
                
                if media_type == 'image':
                    # Handle image media type
                    prompt = placement.get('prompt', '')
                    url = placement.get('url', '')
                    caption = placement.get('caption', prompt)
                    
                    if url:
                        media_html = f'<figure><img src="{url}" alt="{caption}" />'
                        if caption:
                            media_html += f'<figcaption>{caption}</figcaption>'
                        media_html += '</figure>'
                        print(f"  📸 Created image HTML with URL: {url}")
                    else:
                        print(f"  ⚠️ Missing URL for image, skipping")
                        continue
                elif media_type == 'youtube':
                    # Handle YouTube video
                    video_id = placement.get('videoId', '')
                    caption = placement.get('caption', '')
                    
                    if video_id:
                        media_html = f'<figure><iframe style="aspect-ratio: 16 / 9; width: 100%" src="https://www.youtube.com/embed/{video_id}" title="{caption}" frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen></iframe>'
                        if caption:
                            media_html += f'<figcaption>{caption}</figcaption>'
                        media_html += '</figure>'
                        print(f"  🎥 Created video HTML with ID: {video_id}")
                    else:
                        print(f"  ⚠️ Missing videoId for YouTube video, skipping")
                        continue
                else:
                    print(f"  ⚠️ Unsupported media type: {media_type}, skipping")
                    continue
                
                # Insert the media HTML
                html_content = html_content.replace(
                    insert_before, 
                    f"{media_html}\n{insert_before}"
                )
                print("  ✅ Media inserted successfully")
            
            return html_content
            
        except Exception as e:
            print(f"Error in media population: {str(e)}")
            import traceback
            traceback.print_exc()
            return html_content

def list_available_models():
    """List all available Gemini models"""
    print("Listing available models...")
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        
        models = genai.list_models()
        print("Available models:")
        
        model_count = 0
        for model in models:
            model_count += 1
            print(f"- Name: {model.name}")
            print(f"  Display name: {model.display_name}")
            print(f"  Supported methods: {model.supported_generation_methods}")
            print("-" * 50)
        
        print(f"Total models found: {model_count}")
            
    except Exception as e:
        print(f"Error listing models: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    print("Starting main function...")
    list_available_models()
    
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