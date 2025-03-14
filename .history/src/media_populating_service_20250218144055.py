from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from typing import Dict
import json
import requests
from serper_api import fetch_videos
from wordpress_media_handler import WordPressMediaHandler

class GetImgAIClient:
    def __init__(self):
        self.API_KEY = "key-wHtXSzGfHsJsoJCCS8b1nu5FznStdiRjIq21CtzILjUr6nUl3a6Eryqxq8Q8Dgy12CQB8P8SC6m151riDyPePT8DyiFD1k5"
        self.API_URL = "https://api.getimg.ai/v1/flux-schnell/text-to-image"
        self.GOOGLE_API_KEY = "AIzaSyAgBew-UTCDpKGAb1qidbs0CrfC9nKU9ME"  # Replace with your Gemini API key

    def generate_image(self, prompt: str, width=1024, height=1024, steps=4) -> str:
        """Generates an AI image and uploads it to WordPress."""
        try:
            # Create request payload
            data = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "output_format": "jpeg",
                "response_format": "url"
            }

            # Set request headers
            headers = {
                "Authorization": f"Bearer {self.API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Send API request to GetImg
            response = requests.post(self.API_URL, json=data, headers=headers)
            print("🔹 Full GetImg API Response:", response.text)

            # Handle GetImg API response
            if response.status_code == 200:
                result = response.json()
                if "url" in result:
                    generated_image_url = result["url"]
                    
                    # Upload to WordPress
                    try:
                        wp_handler = WordPressMediaHandler(
                            base_url="https://ruckquest.com",
                            openai_api_key="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"
                        )
                        
                        # Upload and get media ID
                        media_id = wp_handler.upload_image_from_url(generated_image_url)
                        print(f"✅ Image uploaded to WordPress. Media ID: {media_id}")
                        
                        # Get the WordPress URL from the response
                        return f"{media_id}"
                        
                    except Exception as wp_error:
                        print(f"❌ WordPress upload failed: {str(wp_error)}")
                        # Return GetImg URL as fallback
                        return generated_image_url
                else:
                    return "❌ No image URL returned in GetImg response."
            else:
                return f"❌ GetImg API Error: {response.status_code} - {response.text}"

        except Exception as e:
            print(f"Error in image generation process: {str(e)}")
            return f"Error generating image: {str(e)}"

class PostWriterV2:
    def __init__(self):
        # Initialize the LLM with Gemini configuration
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            max_output_tokens=2048,
            google_api_key="AIzaSyAgBew-UTCDpKGAb1qidbs0CrfC9nKU9ME"  # Replace with your Gemini API key
        )
        
        self.img_client = GetImgAIClient()
        
        # Define the image generation tool
        generate_image_tool = Tool(
            name="GenerateImage",
            func=self.img_client.generate_image,
            description="Generates an AI image based on the provided prompt. Returns the URL of the generated image."
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
            max_iterations=3,  # Added to limit iterations
            early_stopping_method="generate"  # Better handling of stopping conditions
        )
        
        # Set up the system message
        self.system_message = """You are a professional blog post editor. Your task is to enhance blog posts with relevant images and videos.
When you receive a blog post:
1. Identify 3-4 key points where media would enhance the narrative
2. For each identified point:
   - Specify the exact text before which the media should be inserted. Media should be inserted at logical break points in the text. Before or after new sections, in between paragraphs, etc.
   - Decide whether an image or video would be more effective for this point
   - For images: Generate a relevant image using the GenerateImage tool
   - For videos: Search for a relevant video using the FetchVideos tool
3. Return a JSON array of media placements, each containing:
   - 'insertBefore': the exact text where media should be inserted
   - 'mediaType': either 'image' or 'video'
   - 'mediaUrl': the URL from either GenerateImage or FetchVideos
   - 'description': a brief description of why this media enhances the content at this point

IMPORTANT:
- Return ONLY the JSON object, nothing else
- The insertBefore value must be an exact copy of text from the blog post
- Choose video for dynamic content like demonstrations, tutorials, or news coverage
- Choose images for concept illustrations, static information, or visual appeal
- Limit to 1-2 videos maximum to avoid overwhelming the reader"""

    def enhance_post(self, blog_post: str) -> str:
        """Enhances the blog post with AI-generated images"""
        try:
            # Create the prompt for the agent
            prompt = f"""
            {self.system_message}
            
            Here's the blog post to enhance:
            {blog_post}
            
            Generate appropriate media and return the JSON object with media placements.
            """
            
            # Run the agent
            response = self.agent.invoke({"input": prompt})
            
            # Add better error handling and JSON parsing
            if not response or "output" not in response:
                print("No valid response from agent")
                return "[]"
                
            try:
                output_text = response["output"]
                start = output_text.find('[')
                end = output_text.rfind(']') + 1
                
                if start == -1 or end == 0:
                    print("No JSON array found in response")
                    return "[]"
                    
                json_str = output_text[start:end]
                # Validate JSON format
                json.loads(json_str)  # This will raise an error if invalid JSON
                return json_str
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {str(e)}")
                print(f"Raw response: {output_text}")
                return "[]"

        except Exception as e:
            print(f"Error enhancing post: {str(e)}")
            return "[]"

    def populate_media_in_html(self, html_content: str) -> str:
        """
        Takes HTML content, enhances it with media, and returns the final HTML
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
                    # The media_url returned from WordPress is already the full URL
                    wordpress_url = placement['mediaUrl']  # Renamed from media_url for clarity
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
    post_writer = PostWriterV2()
    sample_post = """<body>
    <h1>What is a Phase I Environmental Site Assessment?</h1>

    <p>Buying, selling, or refinancing commercial real estate? Then you've likely encountered the term "Phase I Environmental Site Assessment," often shortened to Phase I ESA.  This crucial process is a cornerstone of environmental due diligence, designed to identify potential environmental liabilities associated with a property.  Understanding what a Phase I ESA entails is critical for protecting your investment and avoiding costly surprises down the road.  This comprehensive guide will explain everything you need to know.</p>

    <h2>What is the Purpose of a Phase I ESA?</h2>

    <p>The primary purpose of a Phase I ESA is to identify <strong>Recognized Environmental Conditions (RECs)</strong>.  A REC, as defined by the American Society for Testing and Materials (ASTM) Standard E1527-21 (and its predecessor, E1527-13), is the "presence or likely presence of any hazardous substances or petroleum products in, on, or at a property: (1) due to release to the environment; (2) under conditions indicative of a release to the environment; or (3) under conditions that pose a material threat of a future release to the environment." Simply put, it's about finding evidence of past or present contamination that could impact the property's value or pose health and safety risks.</p>

    <p>A Phase I ESA is *not* about actively testing soil, water, or air. It's a non-intrusive investigation, meaning no samples are collected. It's a historical and records-based review, along with a site reconnaissance. Think of it as detective work to uncover potential environmental concerns.</p>

     <h2>Who Needs a Phase I ESA?</h2>

    <p>A Phase I ESA is typically required or strongly recommended in the following situations:</p>

    <ul>
        <li><strong>Commercial Real Estate Transactions:</strong> Buyers, sellers, and lenders often require a Phase I ESA before finalizing a sale or loan. This protects the buyer from inheriting environmental liabilities and safeguards the lender's collateral.</li>
        <li><strong>Refinancing:</strong> Lenders may require a new Phase I ESA when a property is refinanced, even if one was previously conducted.</li>
        <li><strong>Property Development:</strong> Developers need to understand the environmental condition of a site before starting construction to avoid costly delays and remediation.</li>
        <li><strong>Lease Agreements:</strong> Some lease agreements, particularly for industrial properties, may include clauses requiring a Phase I ESA.</li>
        <li><strong>Government Agencies:</strong> Local, state, or federal agencies may require a Phase I ESA for certain types of projects or permits.</li>
    </ul>

    <p>Essentially, anyone involved in a commercial real estate transaction where potential environmental contamination could be a factor should consider a Phase I ESA.</p>

    <h2>What Does a Phase I ESA Involve?</h2>

    <p>The Phase I ESA process, as outlined in the <a href="https://www.astm.org/e1527-21.html">ASTM E1527-21 standard</a>, generally includes the following key components:</p>

    <h3>1. Records Review:</h3>

    <p>This is the most time-consuming part of the process. The environmental professional will review a wide range of historical and current records, including:</p>
"""
    
    enhanced_post = post_writer.populate_media_in_html(sample_post)
    print(f"Enhanced Post: {enhanced_post}")

if __name__ == "__main__":
    main() 