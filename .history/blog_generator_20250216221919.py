from google import generativeai as genai
from google.generativeai import types
import os

class BlogGenerator:
    def __init__(self):
        # Initialize Gemini client
        genai.configure(api_key="AIzaSyAgBew-UTCDpKGAb1qidbs0CrfC9nKU9ME")
        self.client = genai.Client()
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            generation_config=types.GenerateContentConfig(
                tools=[types.Tool(
                    google_search=types.GoogleSearchRetrieval(
                        dynamic_retrieval_config=types.DynamicRetrievalConfig(
                            dynamic_threshold=0.3  # Lower threshold for blog posts to encourage grounding
                        )
                    )
                )],
                response_modalities=["TEXT"]
            )
        )

    def generate_blog_post(self, keyword: str) -> dict:
        """
        Generates a complete blog post optimized for the given keyword
        
        Returns:
            dict containing:
            - content: The blog post text
            - search_queries: List of related search queries
            - rendered_content: HTML/CSS for search suggestions
        """
        prompt = f"""Using the most up-to-date information from searching the web, write a blog post about: "{keyword}"
        
        The blog post should be 1300-2000 words and include:
        - Current, factual information with specific details
        - A key takeaways section
        - An FAQ section
        - Citations to sources using this format: [text to link](URL)
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            
            result = {
                "content": response.text,
                "search_queries": [],
                "rendered_content": None
            }
            
            if response.candidates[0].grounding_metadata:
                result["search_queries"] = response.candidates[0].grounding_metadata.web_search_queries
                result["rendered_content"] = response.candidates[0].grounding_metadata.search_entry_point.rendered_content
            
            return result
            
        except Exception as e:
            print(f"Error generating blog post: {str(e)}")
            return None

def main():
    generator = BlogGenerator()
    post = generator.generate_blog_post("Who won the Super Bowl this year?")
    
    if post:
        print("\nGenerated Blog Post:")
        print("-" * 50)
        print(post["content"])
        print("\nSearch Queries:")
        for query in post["search_queries"]:
            print(f"- {query}")
        if post["rendered_content"]:
            print("\nSearch Suggestions:")
            print(post["rendered_content"])
    else:
        print("Failed to generate blog post")

if __name__ == "__main__":
    main() 