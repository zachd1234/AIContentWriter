import http.client
import json
import os
from typing import List, Dict, Any, Tuple
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
        
        IMPORTANT: Return ONLY the core phrase with no additional text, labels, or formatting.
        """
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')  # Using a simpler model that's more likely to follow instructions
            response = model.generate_content(prompt)
            core_phrase = response.text.strip()
            
            # Clean up the response if it contains "Core phrase:" or similar prefixes
            prefixes_to_remove = ["core phrase:", "core phrase", "the core phrase is", "the core phrase:"]
            for prefix in prefixes_to_remove:
                if core_phrase.lower().startswith(prefix):
                    core_phrase = core_phrase[len(prefix):].strip()
            
            print(f"Distilled core phrase: {core_phrase}")
            return core_phrase
        except Exception as e:
            print(f"Error using Gemini API: {e}")
            # Fallback to using the blog title as the core phrase
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
    
    def get_autocomplete_suggestions(self, query: str, max_suggestions: int = 10) -> List[str]:
        """Get autocomplete suggestions from Serper API."""
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": query
        })
        headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            conn.request("POST", "/autocomplete", payload, headers)
            res = conn.getresponse()
            data = res.read()
            autocomplete_results = json.loads(data.decode("utf-8"))
            
            # Extract suggestions from the correct format
            suggestions = []
            if "suggestions" in autocomplete_results:
                for item in autocomplete_results["suggestions"]:
                    if "value" in item:
                        suggestions.append(item["value"])
            
            print(f"Autocomplete suggestions for '{query}': {suggestions}")
            return suggestions[:max_suggestions]
        except Exception as e:
            print(f"Error getting autocomplete suggestions: {e}")
            return []
    
    def generate_website_categories(self, blog_title: str, blog_description: str) -> str:
        """Use Gemini to generate categories of websites that would be good backlink prospects."""
        prompt = f"""
        Blog Title: {blog_title}
        Blog Description: {blog_description}
        
        Given the above blog about {self.distill_to_core_phrase(blog_title, blog_description)}, 
        what are some types of websites that it could reach out to for backlinks?
        
        For example, if this is a blog about gardening, potential website categories might include:
        - Gardening supply stores and nurseries
        - Plant identification resources
        - Sustainable living websites
        - Home improvement blogs
        - Local agricultural extension offices
        - Large news sites 
        
        List 8-10 specific categories of websites that would be good backlink prospects.
        """
        
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')
            response = model.generate_content(prompt)
            categories_text = response.text.strip()
            print(f"Generated website categories:\n{categories_text}")
            return categories_text
        except Exception as e:
            print(f"Error generating website categories: {e}")
            return ""

    def structure_categories_to_search_terms(self, categories_text: str, core_phrase: str) -> List[Dict[str, str]]:
        """Use Gemini to structure categories into search terms with JSON output."""
        prompt = f"""
        Core Topic: {core_phrase}
        Website Categories:
        {categories_text}
        
        For each of the above website categories, create a structured JSON object with:
        1. The category name
        2. 1-2 specific search queries that would help find websites in that category
        
        The search queries should be specific enough to find relevant websites but general enough to return a good number of results.
        
        Return a valid JSON array where each object has the format:
        {{
          "category": "Category Name",
          "search_terms": ["Search Query 1", "Search Query 2"]
        }}
        
        IMPORTANT: Ensure the output is valid JSON that can be parsed directly.
        """
        
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(prompt)
            json_text = response.text.strip()
            
            # Clean up the response to ensure it's valid JSON
            # Remove markdown code block markers if present
            if json_text.startswith("```json"):
                json_text = json_text.split("```json", 1)[1]
            if json_text.startswith("```"):
                json_text = json_text.split("```", 1)[1]
            if json_text.endswith("```"):
                json_text = json_text.rsplit("```", 1)[0]
            
            json_text = json_text.strip()
            
            # Parse the JSON
            structured_categories = json.loads(json_text)
            print(f"Successfully structured categories into {len(structured_categories)} search term objects")
            return structured_categories
        except Exception as e:
            print(f"Error structuring categories to search terms: {e}")
            print(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
            return []

    def generate_llm_based_prospects(self, blog_title: str, blog_description: str) -> List[Dict[str, str]]:
        """Generate prospects using LLM-generated website categories and search terms."""
        # Get the core phrase
        core_phrase = self.distill_to_core_phrase(blog_title, blog_description)
        
        # Generate website categories (raw text)
        categories_text = self.generate_website_categories(blog_title, blog_description)
        
        # Structure categories into search terms
        structured_categories = self.structure_categories_to_search_terms(categories_text, core_phrase)
        
        # Process results to create unique prospects
        prospects = []
        seen_domains = set()
        
        # Extract all search terms from the structured categories
        search_terms = []
        for category in structured_categories:
            if "search_terms" in category and isinstance(category["search_terms"], list):
                search_terms.extend(category["search_terms"])
        
        # Search for each term and collect results
        for term in search_terms:
            print(f"Searching for: '{term}'")
            search_results = self.search_serper(term)
            
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
                            "url": base_url,
                            "title": title,
                            "snippet": snippet,
                            "search_term": term
                        })
        
        print(f"Generated {len(prospects)} unique prospects using LLM-based search terms")
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
    
    # Test the original method
    print("\n=== TESTING ORIGINAL METHOD ===")
    original_prospects = generator.generate_prospects(blog_title, blog_description)
    print(f"\nGenerated {len(original_prospects)} prospects using original method")
    
    # Test the new LLM-based method
    print("\n=== TESTING LLM-BASED METHOD ===")
    llm_prospects = generator.generate_llm_based_prospects(blog_title, blog_description)
    
    # Print the list of LLM-based prospects
    print("\nLLM-Based Prospect List:")
    for i, prospect in enumerate(llm_prospects, 1):
        print(f"{i}. {prospect['title']}")
        print(f"   URL: {prospect['url']}")
        print(f"   Found via: {prospect['search_term']}")
        print()
    
    # Combine unique prospects from both methods
    all_prospects = []
    seen_domains = set()
    
    # Add original prospects
    for prospect in original_prospects:
        domain = prospect['url']
        if domain not in seen_domains:
            seen_domains.add(domain)
            all_prospects.append(prospect)
    
    # Add LLM-based prospects
    for prospect in llm_prospects:
        domain = prospect['url']
        if domain not in seen_domains:
            seen_domains.add(domain)
            all_prospects.append(prospect)
    
    print(f"\nTotal unique prospects from both methods: {len(all_prospects)}")

if __name__ == "__main__":
    main()
