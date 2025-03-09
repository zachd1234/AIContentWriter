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
from src.api.serper_api import fetch_videos
from src.api.wordpress_media_api import WordPressMediaHandler
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
                        "locationId": {"type": "INTEGER"},
                        "position": {
                            "type": "STRING",
                            "enum": ["before", "after"]
                        },
                        "mediaType": {
                            "type": "STRING",
                            "enum": ["image", "video"]
                        },
                        "mediaUrl": {"type": "STRING"},
                        "description": {"type": "STRING"}
                    },
                    "required": ["locationId", "position", "mediaType", "mediaUrl", "description"]
                }
            }

            # Extract all headings and section starts to provide as insertion points
            import re
            
            # Find all headings (h1-h6)
            heading_pattern = r'<h[1-6][^>]*>(.*?)<\/h[1-6]>'
            headings = re.findall(heading_pattern, blog_post)
            
            # Find all paragraph starts that could be section beginnings
            paragraph_pattern = r'<p[^>]*>(.*?)<\/p>'
            paragraphs = re.findall(paragraph_pattern, blog_post)
            
            # Create a list of potential insertion points with IDs
            potential_insertion_points = []
            
            # Add headings first (they're more likely to be section starts)
            for heading in headings:
                # Clean HTML tags from heading
                clean_heading = re.sub(r'<[^>]+>', '', heading)
                if clean_heading.strip():
                    potential_insertion_points.append({
                        "id": len(potential_insertion_points) + 1,
                        "text": clean_heading.strip(),
                        "type": "heading"
                    })
            
            # Add paragraphs that might start sections
            # (first paragraph after a heading, or paragraphs with strong/bold text at start)
            for paragraph in paragraphs:
                # Clean HTML tags but keep track if it starts with bold/strong
                is_section_start = "<strong>" in paragraph[:50] or "<b>" in paragraph[:50]
                clean_para = re.sub(r'<[^>]+>', '', paragraph)
                
                if clean_para.strip() and (is_section_start or len(potential_insertion_points) < 5):
                    potential_insertion_points.append({
                        "id": len(potential_insertion_points) + 1,
                        "text": clean_para.strip()[:100],  # Take first 100 chars max
                        "type": "paragraph"
                    })
            
            # Print the potential insertion points for debugging
            print("\n🔍 Potential insertion points:")
            for point in potential_insertion_points:
                print(f"  ID {point['id']} ({point['type']}): \"{point['text'][:50]}...\"")
            
            # Format the insertion points for the prompt
            insertion_points_text = "\n".join([
                f"- ID {point['id']}: \"{point['text'][:50]}...\" ({point['type']})" 
                for point in potential_insertion_points
            ])

            # Create the prompt for the agent with clearer instructions
            prompt = f"""
            {self.system_message}
            
            Here's the blog post to enhance:
            {truncated_post}

            INSTRUCTIONS FOR USING TOOLS:
            1. Review the list of section headings and important paragraphs below
            2. Choose 2-3 sections that would benefit most from media enhancement
            3. For each chosen section, decide whether an image or video would be most helpful
            4. Use the appropriate tool (GenerateImage or GetYouTubeVideo) to create that media
            5. After using all tools, compile your results into a JSON array
            
            Each media placement MUST:
            - Directly help readers understand the content or provide valuable visual context
            - Be placed either before or after a section heading or important paragraph
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

            AVAILABLE INSERTION POINTS:
            {insertion_points_text}

            FINAL OUTPUT FORMAT:
            After using the tools, return ONLY a JSON array with this EXACT format:
            [
              {{
                "locationId": 3,
                "position": "before",
                "mediaType": "image",
                "mediaUrl": "https://example.com/image.jpg",
                "description": "explanation of how this helps"
              }},
              {{
                "locationId": 7,
                "position": "after",
                "mediaType": "video",
                "mediaUrl": "https://youtube.com/watch?v=abcdef",
                "description": "explanation of how this helps"
              }}
            ]

            IMPORTANT RULES FOR FINAL OUTPUT:
            1. For images, the mediaUrl must be the URL returned by GenerateImage
            2. For videos, the mediaUrl must be the YouTube URL returned by GetYouTubeVideo
            3. The "locationId" MUST be one of the IDs from the list of available insertion points
            4. The "position" must be either "before" or "after" the specified location
            5. Do NOT include any explanatory text, code blocks, or backticks
            6. Return ONLY the JSON array
            """

            # Configure genai with API key
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            
            # Create the model with structured output configuration
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-001",
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
                # Store the original location ID and position
                location_id = item["locationId"]
                position = item["position"]
                
                # Find the corresponding insertion point text
                insertion_point = next((p for p in potential_insertion_points if p["id"] == location_id), None)
                
                if insertion_point:
                    # Add the insertion point text to the item for later use
                    item["insertionPoint"] = insertion_point
                    
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
                else:
                    print(f"⚠️ Invalid location ID: {location_id}")

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
                
                # Get the insertion point information
                insertion_point = placement.get("insertionPoint", {})
                location_id = placement.get("locationId")
                position = placement.get("position", "before")
                media_type = placement.get("mediaType")
                
                print(f"  Type: {media_type}")
                print(f"  Location ID: {location_id}")
                print(f"  Position: {position}")
                
                if not insertion_point:
                    print("  ❌ Missing insertion point information")
                    continue
                    
                # Get the text to search for
                search_text = insertion_point.get("text", "")[:50]  # Use first 50 chars for searching
                print(f"  Searching for: \"{search_text}...\"")
                
                # Find the text in the content
                import re
                
                # Clean the search text of any HTML tags and escape regex special chars
                clean_search_text = re.sub(r'<[^>]+>', '', search_text)
                clean_search_text = re.escape(clean_search_text)
                
                # Try to find the text in the HTML content
                matches = list(re.finditer(clean_search_text, html_content, re.IGNORECASE))
                
                if matches:
                    # Use the first match
                    match = matches[0]
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    print(f"  ✅ Found text at position {start_pos}")
                    
                    # If it's a heading, try to find the complete heading tag
                    if insertion_point.get("type") == "heading":
                        # Look for the nearest heading tag before this position
                        heading_start = max(
                            html_content.rfind("<h1", 0, start_pos),
                            html_content.rfind("<h2", 0, start_pos),
                            html_content.rfind("<h3", 0, start_pos),
                            html_content.rfind("<h4", 0, start_pos),
                            html_content.rfind("<h5", 0, start_pos),
                            html_content.rfind("<h6", 0, start_pos)
                        )
                        
                        if heading_start != -1:
                            # Find the end of this heading tag
                            heading_end = html_content.find("</h", heading_start)
                            if heading_end != -1:
                                heading_end = html_content.find(">", heading_end) + 1
                                
                                # Update positions based on the complete heading tag
                                if position == "before":
                                    start_pos = heading_start
                                else:  # after
                                    start_pos = heading_end
                    else:
                        # For paragraphs, find the complete paragraph tag
                        para_start = html_content.rfind("<p", 0, start_pos)
                        if para_start != -1:
                            para_end = html_content.find("</p>", start_pos)
                            if para_end != -1:
                                para_end += 4  # Include the </p> tag
                                
                                # Update positions based on the complete paragraph tag
                                if position == "before":
                                    start_pos = para_start
                                else:  # after
                                    start_pos = para_end
                    
                    # Create the media HTML
                    if media_type == 'image':
                        wordpress_url = placement['mediaUrl']
                        media_html = f'<img src="{wordpress_url}" alt="{placement.get("description", "")}" />'
                    else:  # video
                        video_url = placement['mediaUrl']
                        media_html = f'[embed]{video_url}[/embed]'
                    
                    # Insert the media at the specified position
                    if position == "before":
                        html_content = html_content[:start_pos] + f"\n{media_html}\n\n" + html_content[start_pos:]
                    else:  # after
                        html_content = html_content[:start_pos] + f"\n\n{media_html}\n" + html_content[start_pos:]
                    
                    print(f"  ✅ Media inserted {position} the {insertion_point.get('type')}")
                else:
                    print(f"  ❌ Could not find text: '{search_text}'")
            
            return html_content
            
        except Exception as e:
            print(f"Error in media population: {str(e)}")
            return html_content

def main():
   post_writer = PostWriterV2(base_url="https://ruckquest.com")
   sample_post = """""<p>Rucking, the act of walking or hiking with a weighted backpack, has exploded in popularity as a fantastic way to build strength, endurance, and mental toughness. But as with any fitness activity, the gear can sometimes be a barrier.  If you're looking to get started with rucking without breaking the bank, you're in the right place. This guide dives deep into the world of <strong>cheap rucking backpacks</strong>, exploring how to find a functional and affordable pack that won't compromise your training or comfort.</p>

    <h2>Why Choose a Cheap Rucking Backpack?</h2>

    <p>Before we dive into specific recommendations, let's address the elephant in the room: why even consider a cheap rucking backpack?  There are several compelling reasons:</p>

    <ul>
        <li><strong>Cost-Effectiveness:</strong> This is the most obvious benefit.  Rucking doesn't need to be expensive.  A cheaper backpack allows you to allocate your budget to other essential gear or fitness pursuits.</li>
        <li><strong>Beginner-Friendly:</strong> If you're new to rucking, you might not want to invest heavily in high-end gear right away. A budget-friendly backpack is a great way to test the waters and see if rucking is for you without a significant financial commitment.</li>
        <li><strong>Durability is Relative:</strong>  While top-tier backpacks boast incredible resilience, many "cheap" backpacks are surprisingly durable for their price, especially for beginners or those rucking less frequently.</li>
        <li><strong>Versatility:</strong> A cheaper, more basic backpack can often double as an everyday carry bag, travel backpack, or emergency preparedness kit, adding to its overall value.</li>
    </ul>

    <h2>Understanding "Cheap": Setting Realistic Expectations</h2>

    <p>Let's be honest: "cheap" is subjective. What one person considers affordable might be expensive to another.  When we talk about <strong>cheap rucking backpacks</strong>, we're generally referring to backpacks that are significantly less expensive than premium, purpose-built rucking packs like those from GORUCK.  These premium packs can easily cost several hundred dollars.</p>

    <p>A "cheap" rucking backpack might fall into these categories:</p>
    <ul>
        <li><strong>Under $50:</strong>  This range often includes basic backpacks from general retailers, military surplus options, and potentially some budget-oriented brands. Expect compromises in features and potentially durability.</li>
        <li><strong>$50 - $100:</strong>  In this range, you'll find more robust options from established outdoor brands or budget-focused tactical gear companies.  You can expect better materials, more features, and improved comfort compared to the under $50 category.</li>
        <li><strong>$100 - $150:</strong>  While still considered "cheap" relative to high-end rucking packs, this price point opens up access to backpacks with decent durability, specific rucking features (like plate pockets), and reputable brand names.</li>
    </ul>

    <p>It's crucial to understand that with cheaper backpacks, <strong>trade-offs are inevitable</strong>. You might sacrifice:</p>

    <ul>
        <li><strong>Material Durability:</strong> Cheaper backpacks might use thinner nylon or polyester, which could be less resistant to abrasion and tearing over the long term.</li>
        <li><strong>Stitching and Construction:</strong>  Reinforced stitching and robust construction are hallmarks of high-end packs. Cheaper options may have simpler stitching and less overall reinforcement.</li>
        <li><strong>Comfort Features:</strong>  Advanced features like padded hip belts, load lifter straps, and highly breathable back panels might be absent or less refined in budget-friendly packs.</li>
        <li><strong>Warranty:</strong>  Cheaper brands may offer limited or no warranties compared to premium brands known for their lifetime guarantees.</li>
    </ul>

    <p>However, these trade-offs don't necessarily mean a cheap backpack is unusable for rucking. It simply means you need to be more discerning in your selection and understand the limitations.</p>

    <h2>Key Features to Look for in a Cheap Rucking Backpack</h2>

    <p>Even when on a budget, certain features are essential for a functional and safe rucking backpack. Prioritize these aspects:</p>

    <ul>
        <li><strong>Capacity:</strong>  A capacity of 20-30 liters is generally sufficient for rucking, offering enough space for weight plates, water, and essentials.  Consider a larger capacity (30-40L) if you plan on longer rucks or overnight trips.</li>
        <li><strong>Durable Material:</strong> Look for backpacks made from reasonably durable materials like 600D polyester or similar. While not as robust as 1000D Cordura found in premium packs, these materials can hold up for most rucking activities, especially for beginners.</li>
        <li><strong>Sturdy Straps:</strong>  Shoulder straps are crucial for comfort and weight distribution.  Look for padded straps that are at least 2-3 inches wide and ideally reinforced at stress points. A sternum strap is highly recommended to keep the shoulder straps in place.</li>
        <li><strong>Reinforced Stitching:</strong> Examine the stitching, especially at stress points like strap attachment points and seams. Double stitching or bar-tacking indicates better durability.</li>
        <li><strong>Frame Sheet (Optional but Recommended):</strong>  A frame sheet, even a basic plastic one, helps distribute weight more evenly across your back and provides structure to the backpack. Some cheaper backpacks might lack this, but it significantly improves comfort, especially with heavier loads.</li>
        <li><strong>Water Resistance (Desirable):</strong> While not essential, some degree of water resistance is beneficial to protect your gear from light rain or sweat. Look for backpacks with water-resistant coatings or materials.</li>
    </ul>

    <h2>Types of Cheap Rucking Backpacks and Recommendations</h2>

    <p>Now, let's explore different types of backpacks that can serve as <strong>cheap rucking backpacks</strong>, along with some examples and considerations:</p>

    <h3>1. Military Surplus Backpacks (ALICE Packs)</h3>

    <p><strong>Pros:</strong>  Extremely durable, battle-tested, often very affordable, classic rucking look.</p>
    <p><strong>Cons:</strong>  Can be heavy and bulky, might lack modern comfort features, potentially worn condition depending on source.</p>
    <p><strong>Example:</strong>  <strong>ALICE (All-Purpose Lightweight Individual Carrying Equipment) Packs</strong> are a classic military surplus option.  They are incredibly robust and designed to carry heavy loads.  Surplus ALICE packs can often be found at very reasonable prices. According to <a href="https://honehealth.com/edge/best-rucking-backpack/?srsltid=AfmBOorkqtdX_r5qivefjxTxjBhpYcTKZaflHn-XD8Xe-cucmiC8K8CK">Hone Health's review of best rucking backpacks</a>, ALICE packs are frequently recommended as affordable rucking options.</p>
    <p><strong>Considerations:</strong>  ALICE packs are known for their durability but prioritize function over comfort compared to modern backpacks.  Consider upgrading the shoulder straps and hip belt for improved comfort if you plan on longer rucks.</p>

    <h3>2. Budget Tactical Backpacks (5.11 Rush Series Alternatives)</h3>

    <p><strong>Pros:</strong> Tactical styling, MOLLE webbing for customization, often reasonably durable for the price, widely available.</p>
    <p><strong>Cons:</strong>  Quality can vary significantly between brands, some may prioritize aesthetics over true durability, can be heavier than non-tactical packs.</p>
    <p><strong>Example:</strong>  The <strong>5.11 Tactical Rush 12</strong> is a popular entry-level tactical backpack often recommended for rucking.  While the Rush 12 itself might be in the mid-range price category, many brands offer similar-looking tactical backpacks at lower price points on platforms like Amazon.  As mentioned by <a href="https://rucking.com/best-rucking-gear-on-amazon-com/">Rucking.com's article on best rucking gear on Amazon</a>, the 5.11 Rush 12 is a solid low-cost option. Search for "tactical backpack 20L" or "military style backpack" on online retailers to find budget alternatives.</p>
    <p><strong>Considerations:</strong>  Read reviews carefully before purchasing a budget tactical backpack. Focus on reviews that mention durability and load-bearing capacity, not just aesthetics.</p>

    <h3>3. Hiking and Daypacks (Osprey Daylite Plus)</h3>

    <p><strong>Pros:</strong>  Lightweight, comfortable for hiking, often versatile for everyday use, reputable brands available at reasonable prices.</p>
    <p><strong>Cons:</strong>  Might lack dedicated rucking features like plate pockets, durability may be optimized for lighter hiking loads rather than heavy rucking weights.</p>
    <p><strong>Example:</strong> The <strong>Osprey Daylite Plus</strong>, as highlighted by <a href="https://www.ruckliving.com/rucking-detail/affordable-rucking-pack-how-to-choose-one">Ruckliving's guide to affordable rucking packs</a>, is a lightweight and affordable option suitable for shorter rucks or everyday carry.  Brands like <strong>REI Co-op, Deuter, and Gregory</strong> also offer daypacks in the $50-$100 range that could work well for light to moderate rucking.</p>
    <p><strong>Considerations:</strong>  Daypacks are generally designed for lighter loads.  Ensure the straps and construction are robust enough for the weight you plan to carry.  You may need to get creative with weight plate placement as they might not have dedicated pockets.</p>

    <h3>4. Repurposed School Backpacks or General Backpacks</h3>

    <p><strong>Pros:</strong>  Extremely affordable (you might already own one!), readily available, can be a great starting point for trying rucking.</p>
    <p><strong>Cons:</strong>  Often lack durability for heavy loads, comfort may be limited, not designed for rucking, may wear out quickly with regular rucking.</p>
    <p><strong>Example:</strong>  Your old school backpack or a basic backpack from a department store can work in a pinch, especially for very light rucking or as a temporary solution.  As seen in a <a href="https://www.reddit.com/r/Rucking/comments/13hdlan/budget_backpack_recommendation_31_new/">Reddit thread on budget backpacks</a>, even very affordable backpacks can serve as starter rucking packs.</p>
    <p><strong>Considerations:</strong>  Use repurposed backpacks for light rucking only.  Monitor for wear and tear closely, especially at stress points.  Prioritize safety and comfort; upgrade to a more suitable backpack if you plan to ruck regularly.</p>

    <h2>Tips for Maximizing Your Budget Rucking Backpack</h2>

    <p>Once you've chosen a cheap rucking backpack, here are some tips to get the most out of it:</p>

    <ul>
        <li><strong>Weight Plate Placement:</strong> Securely position weight plates close to your back to minimize bouncing and improve weight distribution.  Wrap plates in towels or use soft weight bags to prevent them from shifting and causing discomfort.</li>
        <li><strong>Padding and Comfort:</strong>  Add extra padding to shoulder straps or the back panel if needed.  Use foam pads, old t-shirts, or even cut-up yoga mats to enhance comfort.</li>
        <li><strong>Regular Inspection:</strong>  Frequently inspect your backpack for signs of wear and tear, especially stitching, straps, and zippers.  Address any issues promptly to prevent failures during rucks.</li>
        <li><strong>Start Light, Progress Gradually:</strong>  Don't overload a cheap backpack right away.  Start with lighter weights and gradually increase the load as you get stronger and more confident in your backpack's durability.</li>
        <li><strong>Consider DIY Modifications:</strong>  If you're handy, you can reinforce stitching, add straps, or create DIY weight plate compartments to improve the functionality and durability of your cheap backpack.</li>
    </ul>

    <h2>Key Takeaways: Rucking on a Budget</h2>

    <ul>
        <li><strong>"Cheap" rucking backpacks are achievable:</strong> You don't need to spend a fortune to start rucking. Functional and affordable options are available.</li>
        <li><strong>Prioritize essential features:</strong> Focus on durability, comfortable straps, and sufficient capacity, even in budget backpacks.</li>
        <li><strong>Consider different types:</strong> Military surplus, budget tactical packs, hiking daypacks, and even repurposed backpacks can work as cheap rucking backpacks.</li>
        <li><strong>Manage expectations and trade-offs:</strong> Understand that cheaper backpacks may have limitations in durability and comfort compared to premium options.</li>
        <li><strong>Maximize your budget pack:</strong> Use smart weight placement, add padding, inspect regularly, and start light to get the most out of your cheap rucking backpack.</li>
    </ul>

    <h2>FAQ: Cheap Rucking Backpacks</h2>

    <dl>
        <dt><strong>Q: Can I really ruck with a cheap backpack?</strong></dt>
        <dd><strong>A:</strong> Yes, absolutely! Many people successfully ruck with budget-friendly backpacks. The key is to choose wisely, prioritize essential features, and understand the potential limitations. Start with lighter weights and gradually increase as needed.</dd>

        <dt><strong>Q: What's the cheapest type of backpack for rucking?</strong></dt>
        <dd><strong>A:</strong> Repurposed backpacks (like old school backpacks) are the cheapest, as you might already own one. Military surplus backpacks like ALICE packs are also very affordable and durable options.</dd>

        <dt><strong>Q: Are tactical backpacks good for rucking?</strong></dt>
        <dd><strong>A:</strong> Yes, tactical backpacks can be excellent for rucking due to their robust construction and often ample features like MOLLE webbing. However, quality varies, so research specific models and read reviews. Budget tactical backpacks can be a good value.</dd>

        <dt><strong>Q: Where can I find cheap rucking backpacks?</strong></dt>
        <dd><strong>A:</strong> Check online retailers like Amazon, eBay, and military surplus stores. Local sporting goods stores and department stores may also have budget-friendly backpacks that can be adapted for rucking.</dd>

        <dt><strong>Q: Is it worth investing in a more expensive rucking backpack?</strong></dt>
        <dd><strong>A:</strong> It depends on your rucking frequency, intensity, and budget. If you plan to ruck regularly with heavy weights, a more durable and comfortable purpose-built rucking backpack might be a worthwhile long-term investment. However, for beginners or occasional ruckers, a cheap backpack can be a great starting point.</dd>
    </dl>

    <h2>Conclusion: Smart Budget Rucking</h2>

    <p>Rucking is about getting outside, challenging yourself, and building resilience. It shouldn't be financially prohibitive.  By being informed and strategic, you can absolutely find a <strong>cheap rucking backpack</strong> that meets your needs and allows you to enjoy all the benefits of this fantastic fitness activity.  Remember to prioritize functionality, safety, and smart choices over simply chasing the lowest price tag. Happy rucking!</p>

</body>
</html>"""


   enhanced_post = post_writer.populate_media_in_html(
       sample_post
   )
   print(f"Enhanced Post: {enhanced_post}")


if __name__ == "__main__":
   main()