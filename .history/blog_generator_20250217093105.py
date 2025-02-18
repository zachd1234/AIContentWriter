import google.generativeai as genai
import os
from typing import Dict

class BlogGenerator:
    def __init__(self):
        # Initialize Gemini
        genai.configure(api_key="AIzaSyAgBew-UTCDpKGAb1qidbs0CrfC9nKU9ME")
        self.model = genai.GenerativeModel('gemini-2.0-pro-exp-02-05')

    def generate_blog_post(self, keyword: str) -> dict:
        """
        Generates a complete blog post optimized for the given keyword
        """
        prompt = f"""You are an expert on the topic and your goal is to write a blog post that ranks 1st on Google for the keyword: "{keyword}"

        Write a 1300-2000 word blog post for this keyword. Include a key takeaway and FAQ section. 
        If you reference a source in the content, add an external link to it using anchor text that accurately describes the source or its relevance.

        External Link Format: [text to link](URL)
        Example: According to [research from Harvard Medical School](https://harvard.edu/study), rucking improves cardiovascular health.

        Return only the blog post content, with external links properly formatted.
        """
        
        try:
            response = self.model.generate_content(contents=prompt)
            return {
                "content": response.text
            }
            
        except Exception as e:
            print(f"Error generating blog post: {str(e)}")
            return None

    async def convert_to_html(self, raw_content: str) -> str:
        """
        Converts raw content to properly formatted HTML
        
        Args:
            raw_content (str): The raw blog post content
            
        Returns:
            str: HTML formatted version of the content
        """
        prompt = f"""Convert this blog post to clean, semantic HTML.
        Use these HTML elements appropriately:
        - <article> for the main content
        - <h1> for the main title
        - <h2> for section headers
        - <p> for paragraphs
        - <strong> for important terms
        - <ul> and <li> for lists
        - <blockquote> for quotes
        
        Output only the HTML, no explanations.
        
        Here's the content to convert:
        
        {raw_content}
        """
        
        try:
            response = self.model.generate_content(contents=prompt)
            return response.text
            
        except Exception as e:
            print(f"Error converting to HTML: {str(e)}")
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
        
        # Step 2: Convert to HTML
        if raw_post:
            html_content = await self.convert_to_html(raw_post["content"])
            return html_content
        
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