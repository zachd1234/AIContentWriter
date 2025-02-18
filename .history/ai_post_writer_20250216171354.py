from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from typing import Dict
import json

class GetImgAIClient:
    def generate_image(self, prompt: str) -> str:
        """
        Custom image generation tool - replace with your actual implementation
        """
        try:
            print(f"Generating image with custom tool for prompt: {prompt}")
            return f"http://example.com/generated-image-for-{prompt}.jpg"
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return f"Error generating image: {str(e)}"

class PostWriterV2:
    def __init__(self):
        # Initialize the LLM
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            api_key="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"
        )
        
        self.img_client = GetImgAIClient()
        
        # Define the image generation tool
        generate_image_tool = Tool(
            name="GenerateImage",
            func=self.img_client.generate_image,
            description="Generates an image based on the provided prompt. Returns the URL of the generated image."
        )
        
        # Initialize the agent with the tool
        self.agent = initialize_agent(
            tools=[generate_image_tool],
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )
        
        # Set up the system message
        self.system_message = """You are a professional blog post editor. Your task is to enhance blog posts with relevant images.
When you receive a blog post:
1. Identify 2-3 key points where images would enhance the narrative
2. For each identified point:
   - Specify the exact text before which the image should be inserted
   - Generate a relevant image using the GenerateImage tool
3. Return a JSON array of image placements, each containing:
   - 'insertBefore': the exact text where image should be inserted
   - 'imageUrl': the URL from GenerateImage

IMPORTANT:
- Return ONLY the JSON object, nothing else
- Do not add any descriptions or commentary
- Do not modify the original text
- Do not create new text
- The insertBefore value must be an exact copy of text from the blog post"""

    def enhance_post(self, blog_post: str) -> str:
        """Enhances the blog post with AI-generated images"""
        try:
            # Create the prompt for the agent
            prompt = f"""
            {self.system_message}
            
            Here's the blog post to enhance:
            {blog_post}
            
            Generate appropriate images and return the JSON object with image placements.
            """
            
            # Run the agent
            response = self.agent.invoke({"input": prompt})
            return response["output"]

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