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

    def generate_complete_prospect_report(self, blog_title: str, blog_description: str) -> Dict[str, Any]:
        """
        Complete control panel method that generates a full prospect report.
        
        This method:
        1. Distills the blog to a core phrase
        2. Generates website categories
        3. Structures those categories into search terms
        4. Searches for websites in each category
        5. Returns a complete report with all results
        
        Args:
            blog_title: The title of the blog
            blog_description: The description of the blog
            
        Returns:
            A complete prospect report with all categories and websites
        """
        # First, generate the prospect plan
        print("\n=== GENERATING PROSPECT PLAN ===")
        prospect_plan = self.generate_prospect_plan(blog_title, blog_description)
        
        # Then, execute searches based on the plan
        print("\n=== EXECUTING SEARCHES BASED ON PLAN ===")
        results = self.generate_prospects_from_plan(prospect_plan)
        
        # Return the complete results
        return results

    def generate_prospect_plan(self, blog_title: str, blog_description: str) -> Dict[str, Any]:
        """
        Generate a prospect plan with categories and search terms without performing searches.
        
        This is a control panel method that:
        1. Distills the blog to a core phrase
        2. Generates website categories
        3. Structures those categories into search terms
        4. Returns all this information without performing actual searches
        """
        # Get the core phrase
        core_phrase = self.distill_to_core_phrase(blog_title, blog_description)
        print(f"\nCore phrase: {core_phrase}")
        
        # Generate website categories
        print("\n=== GENERATING WEBSITE CATEGORIES ===")
        categories_text = self.generate_website_categories(blog_title, blog_description)
        
        # Structure categories into search terms
        print("\n=== STRUCTURING CATEGORIES INTO SEARCH TERMS ===")
        structured_categories = self.structure_categories_to_search_terms(categories_text, core_phrase)
        
        # Create the prospect plan
        prospect_plan = {
            "blog_title": blog_title,
            "blog_description": blog_description,
            "core_phrase": core_phrase,
            "categories_text": categories_text,
            "structured_categories": structured_categories
        }
        
        return prospect_plan  


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
        - Gardening blog sites (obviously make sure to include the exact niche as our blog)        
        - Gardening supply stores 
        - Plant identification resources
        - Sustainable living websites
        - Home improvement blogs
        - Large news sites 
        -ect.
        
        List specific categories of websites that would be good backlink prospects.
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
        """Use Gemini to structure categories into search terms with JSON output using schema."""
        prompt = f"""
        Core Topic: {core_phrase}
        Website Categories:
        {categories_text}
        
        For each of the above website categories, create a structured object with:
        1. The category name
        2. One specific search query that would help find websites in that category (e.g. "gardening supplies websites" or "large news sites")
        
        The search query should be specific enough to find relevant websites but general enough to return a good number of results. If a specifc category should be broken into mutiple categories, do that. Do not include fourms as categories.  
        """

        # Define the response schema for structured output
        response_schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "category": {"type": "STRING"},
                    "search_term": {"type": "STRING"}
                },
                "required": ["category", "search_term"]
            }
        }
        
        try:
            # Create the model with structured output configuration
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-001",
                generation_config={
                    "temperature": 0.1,
                }
            )
            
            # Generate structured response
            response = model.generate_content(
                contents=prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": response_schema
                }
            )
            
            # Get the structured output
            structured_categories = json.loads(response.text)
            
            # Manually append the core phrase blog sites category
            core_blog_category = {
                "category": f"{core_phrase} Blog Sites",
                "search_term": f"{core_phrase} blogs"
            }
            
            # Add to the beginning of the list to prioritize it
            structured_categories.insert(0, core_blog_category)
            
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
            if "search_term" in category:
                search_terms.append(category["search_term"])
        
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
                            "search_term": term,
                            "category": next((cat["category"] for cat in structured_categories if cat.get("search_term") == term), "")
                        })
        
        print(f"Generated {len(prospects)} unique prospects using LLM-based search terms")
        return prospects

    def generate_website_list(self, search_term: str, category: str, all_websites: set) -> List[Dict[str, Any]]:
        """
        Generate a list of websites for a specific category and search term.
        
        Args:
            search_term: The search term to use for finding websites
            category: The category name these websites belong to
            all_websites: A set of all websites found so far (for deduplication)
            
        Returns:
            A list of unique website objects for this category
        """
        print(f"Searching for '{search_term}' in category '{category}'...")
        
        # Search using the Serper API
        try:
            search_results = self.search_serper(search_term)
            print(f"Serper API returned {len(search_results)} results")
            
            # Debug: Print the first result if available
            if search_results and len(search_results) > 0:
                print(f"First result: {search_results[0].get('title', 'No title')} - {search_results[0].get('link', 'No link')}")
            else:
                print("No results returned from Serper API")
        except Exception as e:
            print(f"Error searching Serper API: {e}")
            search_results = []
        
        # Process results to create unique prospects for this category
        category_websites = []
        
        for result in search_results:
            url = result.get("link")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            
            if url:
                # Extract the base URL (domain)
                try:
                    parsed_url = urlparse(url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    
                    # Check if this website is already in our global list
                    if base_url not in all_websites:
                        # Add to global list for future deduplication
                        all_websites.add(base_url)
                        
                        # Add to this category's list
                        category_websites.append({
                            "url": base_url,
                            "title": title,
                            "snippet": snippet,
                            "search_term": search_term,
                            "category": category
                        })
                except Exception as e:
                    print(f"Error processing URL {url}: {e}")
        
        print(f"Found {len(category_websites)} unique websites for '{category}'")
        return category_websites

    def generate_prospects_from_plan(self, prospect_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate prospects from a prospect plan, handling deduplication across categories.
        
        Args:
            prospect_plan: A prospect plan generated by generate_prospect_plan
            
        Returns:
            A dictionary with categorized website lists and statistics
        """
        # Initialize the global set of all websites for deduplication
        all_websites = set()
        
        # Initialize the results structure
        results = {
            "blog_title": prospect_plan["blog_title"],
            "blog_description": prospect_plan["blog_description"],
            "core_phrase": prospect_plan["core_phrase"],
            "categories": [],
            "total_websites": 0
        }
        
        # Process each category in the structured_categories
        print("\n=== SEARCHING FOR WEBSITES BY CATEGORY ===")
        for category_obj in prospect_plan["structured_categories"]:
            category = category_obj.get("category", "Unknown Category")
            search_term = category_obj.get("search_term", "")
            
            if search_term:
                print(f"\nProcessing category: {category}")
                # Generate website list for this category
                websites = self.generate_website_list(search_term, category, all_websites)
                
                # Add to results
                category_result = {
                    "category": category,
                    "search_term": search_term,
                    "websites": websites,
                    "count": len(websites)
                }
                
                results["categories"].append(category_result)
                print(f"Added {len(websites)} websites to category '{category}'")
        
        # Update total count
        results["total_websites"] = len(all_websites)
        print(f"\nTotal unique websites found across all categories: {results['total_websites']}")
        
        return results

    def test_serper_api(self, query: str) -> None:
        """Test the Serper API directly with a given query."""
        print(f"\n=== TESTING SERPER API WITH QUERY: '{query}' ===")
        print(f"Using API key: {self.serper_api_key[:5]}...{self.serper_api_key[-5:]} (length: {len(self.serper_api_key)})")
        
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({
            "q": query,
            "num": 10  # Smaller number for testing
        })
        headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            print("Sending request to Serper API...")
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            print(f"Response status: {res.status} {res.reason}")
            
            data = res.read()
            response_text = data.decode("utf-8")
            print(f"Response length: {len(response_text)} characters")
            
            try:
                search_results = json.loads(response_text)
                print(f"Response keys: {list(search_results.keys())}")
                
                if 'organic' in search_results:
                    organic_results = search_results.get("organic", [])
                    print(f"Found {len(organic_results)} organic results")
                    
                    # Print the first result if available
                    if organic_results and len(organic_results) > 0:
                        first_result = organic_results[0]
                        print("\nFirst result:")
                        print(f"Title: {first_result.get('title', 'No title')}")
                        print(f"Link: {first_result.get('link', 'No link')}")
                        print(f"Snippet: {first_result.get('snippet', 'No snippet')[:100]}...")
                else:
                    print("No 'organic' key found in response")
                    print(f"Full response: {response_text[:500]}...")
            except json.JSONDecodeError:
                print("Failed to parse JSON response")
                print(f"Raw response: {response_text[:500]}...")
        except Exception as e:
            print(f"Error testing Serper API: {e}")

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
    
    # Test the Serper API directly
    generator.test_serper_api("rucking blogs")
    generator.test_serper_api("fitness blogs")
    
    # Ask if user wants to proceed with full report
    proceed = input("\nDo you want to proceed with generating the complete prospect report? (y/n): ")
    
    if proceed.lower() == 'y':
        # Use the control panel method to generate a complete report
        print("\n=== GENERATING COMPLETE PROSPECT REPORT ===")
        report = generator.generate_complete_prospect_report(blog_title, blog_description)
        
        # Display results
        print("\nResults by Category:")
        for i, category_data in enumerate(report["categories"], 1):
            category = category_data["category"]
            count = category_data["count"]
            print(f"\n{i}. {category} ({count} websites)")
            
            # Show top 5 websites for this category
            for j, website in enumerate(category_data["websites"][:5], 1):
                print(f"   {j}. {website['title']}")
                print(f"      URL: {website['url']}")
            
            if count > 5:
                print(f"      ... and {count - 5} more")
        
        print(f"\nTotal unique websites found: {report['total_websites']}")

if __name__ == "__main__":
    main()
