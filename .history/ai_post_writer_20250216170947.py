import json
import openai
from typing import List, Dict
from dataclasses import dataclass
from abc import ABC, abstractmethod

class ConfigManager:
    @staticmethod
    def get_openai_key() -> str:
        # Replace this with your actual config management
        return "your-openai-key-here"

class GetImgAIClient:
    def generate_image(self, prompt: str) -> str:
        try:
            # Using OpenAI's DALL-E API to generate images
            response = openai.Image.create(
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            return response['data'][0]['url']
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return f"Error generating image: {str(e)}"

class PostAgent(ABC):
    @abstractmethod
    def enhance_post_with_images(self, blog_post: str) -> str:
        pass

SYSTEM_MESSAGE = """
You are a professional blog post editor. Your task is to enhance blog posts with relevant images.
When you receive a blog post:
1. Identify 2-3 key points where images would enhance the narrative
2. For each identified point:
   - Specify the exact text before which the image should be inserted
   - Generate a relevant image using the generateImage tool
3. Return a JSON array of image placements, each containing:
   - 'insertBefore': the exact text where image should be inserted
   - 'imageUrl': the URL from generateImage

EXAMPLE OUTPUT FORMAT:
{
  "imagePlacements": [
    {
      "insertBefore": "🎾 The Art and Science of Tennis: A Perfect Blend of Skill and Strategy",
      "imageUrl": "URL_FROM_GENERATE_IMAGE"
    }
  ]
}

IMPORTANT:
- Return ONLY the JSON object, nothing else
- Do not add any descriptions or commentary
- Do not modify the original text
- Do not create new text
- The insertBefore value must be an exact copy of text from the blog post
"""

class PostWriterV2:
    def __init__(self):
        # Initialize OpenAI API
        openai.api_key = ConfigManager.get_openai_key()
        self.img_client = GetImgAIClient()
        
    def generate_image(self, prompt: str) -> str:
        """Generates an image based on the provided prompt and returns the URL"""
        print(f"Generating image for: {prompt}")  # Debug print
        url = self.img_client.generate_image(prompt)
        print(f"Generated URL: {url}")  # Debug print
        return url

    def enhance_post(self, blog_post: str) -> str:
        """Enhances the blog post with AI-generated images"""
        try:
            # Create a conversation with the AI
            messages = [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": blog_post}
            ]

            # Get completion from GPT-4
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                functions=[{
                    "name": "generate_image",
                    "description": "Generates an image based on the provided prompt",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The prompt to generate the image"
                            }
                        },
                        "required": ["prompt"]
                    }
                }],
                function_call="auto"
            )

            # Parse the response and generate images
            result = response.choices[0].message.content
            return result

        except Exception as e:
            print(f"Error enhancing post: {str(e)}")
            return f"Error enhancing post: {str(e)}"

def main():
    post_writer = PostWriterV2()
    sample_post = """🎾 The Art and Science of Tennis: A Perfect Blend of Skill and Strategy

Tennis is more than just a sport—it's a test of endurance, precision, and mental strength. 
Whether played on grass, clay, or hard courts, the game demands a unique combination of 
agility, technique, and strategic thinking.

🎾 The Fundamentals

At its core, tennis is a battle of consistency and power. Players must master essential 
shots such as the forehand, backhand, serve, and volley. Each shot requires precise timing, 
footwork, and tactical placement to outmaneuver an opponent.
"""
    
    enhanced_post = post_writer.enhance_post(sample_post)
    print(f"Enhanced Post: {enhanced_post}")

if __name__ == "__main__":
    main() 