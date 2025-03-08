import http.client
import json
import os
from typing import List, Dict, Any
import google.generativeai as genai
from urllib.parse import urlparse

class ProspectGenerator:
    def __init__(self, serper_api_key: str = None, gemini_api_key: str = None):
        """Initialize the ProspectGenerator with API keys."""
        self.serper_api_key = serper_api_key or os.environ.get("SERPER_API_KEY", "d5dce9e923a550cedc12015627d4d0982801c08b")
        
        # Set up Gemini
        gemini_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
        
    def distill_to_core_phrase(self, blog_title: str, blog_description: str) -> str:
        """Use Gemini to distill the blog content to a single core phrase/word."""
        prompt = f"""
        Blog Title: {blog_title}
        Blog Description: {blog_description}
        
        Distill the above blog content to a single core phrase or word that best represents 
        what this blog is about. For example, if it's about rucking, just return "rucking". 
        If it's about Phase I Environmental Site Assessments, return "Phase I Environmental Site Assessments".
        
        Core phrase:
        """
        
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')
            response = model.generate_content(prompt)
            core_phrase = response.text.strip()
            print(f"Distilled core phrase: {core_phrase}")
            return core_phrase
        except Exception as e:
            print(f"Error using Gemini API: {e}")
            # Fallback to using the blog title as the core phrase
            # If the title is long, just use the first few words
            words = blog_title.split()
            if len(words) > 5:
                return " ".join(words[:5])
            return blog_title
    
    def search_serper(self, query: str, num_results: int = 100) -> List[Dict[Any, Any]]:
        """Search using Serper API with the given query."""
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": query,
            "num": num_results
        })
        headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            data = res.read()
            search_results = json.loads(data.decode("utf-8"))
            return search_results.get("organic", [])
        except Exception as e:
            print(f"Error searching Serper API: {e}")
            return []
    
    def generate_prospects(self, blog_title: str, blog_description: str) -> List[Dict[str, str]]:
        """Generate a list of unique prospects based on the blog content."""
        # Get the core phrase
        core_phrase = self.distill_to_core_phrase(blog_title, blog_description)
        
        # Search for related content
        search_results = self.search_serper(core_phrase)
        
        # Process results to create unique prospects
        prospects = []
        seen_domains = set()
        
        for result in search_results:
            url = result.get("link")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            
            if url:
                # Extract the base URL (domain)
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                if base_url not in seen_domains:
                    seen_domains.add(base_url)
                    prospects.append({
                        "url": base_url,  # Store the base URL instead of the full URL
                        "title": title,
                        "snippet": snippet,
                        "core_phrase": core_phrase
                    })
        
        print(f"Generated {len(prospects)} unique prospects for '{core_phrase}'")
        return prospects

def main():
    """Example usage of the ProspectGenerator."""
    # Example blog
    blog_title = "The Ultimate Guide to Rucking: Benefits, Techniques, and Gear"
    blog_description = """
    Rucking is a simple yet effective exercise that involves walking with a weighted backpack.
    This comprehensive guide covers the health benefits of rucking, proper techniques to avoid injury,
    and essential gear recommendations for beginners and experienced ruckers alike.
    """
    
    generator = ProspectGenerator()
    prospects = generator.generate_prospects(blog_title, blog_description)
    
    # Print the list of prospects
    print("\nProspect List:")
    for i, prospect in enumerate(prospects, 1):
        print(f"   URL: {prospect['url']}")

if __name__ == "__main__":
    main()
