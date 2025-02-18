from typing import List, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
import os

class BlogGenerator:
    def __init__(self):
        # Initialize Gemini with LangChain
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-pro-exp-02-05",
            temperature=0.7,
            max_tokens=8192,
            top_p=0.8,
            top_k=40,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

    def generate_blog_post(self, keyword: str) -> str:
        """
        Generates a complete blog post optimized for the given keyword
        
        Args:
            keyword: The target keyword to optimize for
            
        Returns:
            The complete blog post with external citations
        """
        prompt = f"""You are an expert on the topic and your goal is to write a blog post that ranks 1st on Google for the keyword: "{keyword}"

        Write a 1300-2000 word blog post for this keyword. Include a key takeaway and FAQ section. 
        If you reference a source in the content, add an external link to it using anchor text that accurately describes the source or its relevance.

        External Link Format: [text to link](URL)
        Example: According to [research from Harvard Medical School](https://harvard.edu/study), rucking improves cardiovascular health.

        Return only the blog post content, with external links properly formatted.
        """
        
        try:
            response = self.llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            print(f"Error generating blog post: {str(e)}")
            return None

def main():
    generator = BlogGenerator()
    post = generator.generate_blog_post("How to Start Rucking")
    
    if post:
        print("\nGenerated Blog Post:")
        print("-" * 50)
        print(post)
    else:
        print("Failed to generate blog post")

if __name__ == "__main__":
    main() 