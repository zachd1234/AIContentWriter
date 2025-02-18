from google import generativeai as genai
import os

class BlogGenerator:
    def __init__(self):
        # Initialize Gemini
        genai.configure(api_key="AIzaSyAgBew-UTCDpKGAb1qidbs0CrfC9nKU9ME")
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def generate_blog_post(self, keyword: str) -> dict:
        """
        Generates a complete blog post optimized for the given keyword
        
        Returns:
            dict containing:
            - content: The blog post text
            - search_queries: List of related search queries
            - rendered_content: HTML/CSS for search suggestions
        """
        prompt = f"""Using the most up-to-date information from searching the web RIGHT NOW, write a blog post about: "{keyword}"
        
        IMPORTANT: You must search the web for current information. Do not rely on your training data.
        
        The blog post should be 1300-2000 words and include:
        - Current, factual information with specific details from 2025
        - A key takeaways section
        - An FAQ section
        - Citations to sources using this format: [text to link](URL)
        """
        
        try:
            # Enable search with safety settings
            response = self.model.generate_content(
                contents=prompt,
                safety_settings=[{
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                }],
                tools=[{
                    "function_declarations": [{
                        "name": "web_search",
                        "description": "Search the web for real-time information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query"
                                }
                            },
                            "required": ["query"]
                        }
                    }]
                }]
            )
            
            print("Debug - Full Response:", response)  # Debug logging
            
            result = {
                "content": response.text,
                "search_queries": [],
                "rendered_content": None
            }
            
            if hasattr(response, 'candidates') and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                print("Debug - Metadata:", metadata)  # Debug logging
                result["search_queries"] = metadata.web_search_queries
                result["rendered_content"] = metadata.search_entry_point.rendered_content
            
            return result
            
        except Exception as e:
            print(f"Error generating blog post: {str(e)}")
            print(f"Error type: {type(e)}")  # Debug logging
            return None

def main():
    generator = BlogGenerator()
    post = generator.generate_blog_post("Who won the Super Bowl in 2025?")
    
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