import google.generativeai as genai
from google.generativeai import types  # Add this import
import os
from typing import Dict

class BlogGenerator:
    def __init__(self):
        # Initialize Gemini with your API key
        genai.configure(api_key="AIzaSyAgBew-UTCDpKGAb1qidbs0CrfC9nKU9ME")
        self.model = genai.GenerativeModel('models/gemini-2.0-pro-exp')  # Using newer model

    def generate_blog_post(self, keyword: str) -> dict:
        """
        Generates a complete blog post optimized for the given keyword in HTML format
        """
        prompt = f"""You are an expert on the topic and your goal is to write a blog post that ranks 1st on Google for the keyword: "{keyword}"

        Write a 1300-2000 word blog post for this keyword. Include a key takeaway and FAQ section.
        Format the entire post in clean, semantic HTML using:
        - <h1> for the main title
        - <h2> for section headers
        - <p> for paragraphs
        - <strong> for important terms
        - <ul> and <li> for lists
        - <a href="URL">text</a> for links

        If you reference a source in the content, add an external link using proper <a> tags.
        Example: According to <a href="https://harvard.edu/study">research from Harvard Medical School</a>, rucking improves cardiovascular health.

        Return only the HTML-formatted blog post content.
        """
        
        try:
            # Configure Google Search grounding according to current API version
            response = self.model.generate_content(
                contents=prompt,
                tools=[{
                    "type": "google_search_retrieval",
                    "mode": "auto"
                }]
            )
            
            return {
                "content": response.text
            }
            
        except Exception as e:
            print(f"Error generating blog post: {str(e)}")
            return None

    async def create_complete_post(self, keyword: str) -> str:
        """
        Generates a blog post and converts it to HTML in two steps
        
        Args:
            keyword (str): Main topic of the blog post
            
        Returns:
            str: Final HTML formatted blog post
        """
        # Step 1: Generate raw content
        raw_post = self.generate_blog_post(keyword)
        
        return raw_post
        
        return None

def main():
    generator = BlogGenerator()
    post = generator.generate_blog_post("What is a Phase I Environmental Site Assessment?")
    
    if post:
        print("\nGenerated Blog Post:")
        print("-" * 50)
        print(post["content"])
    else:
        print("Failed to generate blog post")

if __name__ == "__main__":
    main()

print(genai.__version__)  # Print version
model = genai.GenerativeModel('gemini-pro')
# Print available configuration options
print(dir(model.generate_content)) 