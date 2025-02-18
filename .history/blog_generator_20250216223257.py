from google import genai
import os

class BlogGenerator:
    def __init__(self):
        # Initialize Gemini
        genai.configure(api_key="AIzaSyAgBew-UTCDpKGAb1qidbs0CrfC9nKU9ME")
        self.model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-02-05')

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