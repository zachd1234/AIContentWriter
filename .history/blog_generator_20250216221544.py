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
        prompt = f"""You are an expert on the topic and your goal is to write a blog post that ranks 1st on Google for the keyword: "{keyword}"

        Write a 1300-2000 word blog post for this keyword. Include a key takeaway and FAQ section. 
        If you reference a source in the content, add an external link to it using anchor text that accurately describes the source or its relevance.

        External Link Format: [text to link](URL)
        Example: According to [research from Harvard Medical School](https://harvard.edu/study), rucking improves cardiovascular health.

        Return only the blog post content, with external links properly formatted.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                tools=[{
                    "function_declarations": [{
                        "name": "google_search",
                        "description": "Search the web for current information"
                    }]
                }]
            )
            
            result = {
                "content": response.text,
                "search_queries": [],
                "rendered_content": None
            }
            
            # Extract metadata if available using proper response object attributes
            if hasattr(response, 'candidates'):
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, 'web_search_queries'):
                        result["search_queries"] = metadata.web_search_queries
                    if hasattr(metadata, 'search_entry_point'):
                        result["rendered_content"] = metadata.search_entry_point.rendered_content
            
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