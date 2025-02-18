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
        
        Here's the content to convert:
        
        {raw_content}
        """
        
        response = await self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an HTML conversion specialist. Output only valid HTML."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content

    async def create_complete_post(self, keyword: str) -> Dict[str, str]:
        """
        Generates a blog post and converts it to HTML in two steps
        
        Args:
            keyword (str): Main topic of the blog post
            
        Returns:
            Dict[str, str]: Contains both raw content and HTML version
        """
        # Step 1: Generate raw content
        raw_content = await self.generate_post(keyword)
        
        # Step 2: Convert to HTML
        html_content = await self.convert_to_html(raw_content)
        
        return {
            "raw_content": raw_content,
            "html_content": html_content
        }

def main():
    generator = BlogGenerator()
    post = generator.generate_blog_post("Who won the Super Bowl in 2025?")
    
    if post:
        print("\nGenerated Blog Post:")
        print("-" * 50)
        print(post["content"])
    else:
        print("Failed to generate blog post")

if __name__ == "__main__":
    main() 