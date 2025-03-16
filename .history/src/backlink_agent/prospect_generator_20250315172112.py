import http.client
import json
import os
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from urllib.parse import urlparse
import sys

# Add the parent directory to sys.path to import the database_service module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_service import DatabaseService

class ProspectGenerator:
    def __init__(self, serper_api_key: str = None, gemini_api_key: str = None):
        """Initialize the ProspectGenerator with API keys."""
        self.serper_api_key = serper_api_key or os.environ.get("SERPER_API_KEY", "d5dce9e923a550cedc12015627d4d0982801c08b")
        
        # Set up Gemini
        gemini_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
        
        # Initialize database service
        self.db_service = DatabaseService()

    def generate_complete_prospect_report(self, blog_title: str, blog_description: str, site_id: int = None) -> Dict[str, Any]:
        """
        Complete control panel method that generates a full prospect report and saves URLs to database.
        
        This method:
        1. Distills the blog to a core phrase
        2. Generates website categories
        3. Structures those categories into search terms
        4. Searches for websites in each category
        5. Saves the results to the database
        6. Returns a complete report with all results
        
        Args:
            blog_title: The title of the blog
            blog_description: The description of the blog
            site_id: Optional ID of the site to associate with the URLs
            
        Returns:
            A complete prospect report with all categories and websites
        """
        # First, generate the prospect plan
        print("\n=== GENERATING PROSPECT PLAN ===")
        prospect_plan = self.generate_prospect_plan(blog_title, blog_description)
        
        # Then, execute searches based on the plan
        print("\n=== EXECUTING SEARCHES BASED ON PLAN ===")
        results = self.generate_prospects_from_plan(prospect_plan)
        
        # Save the results to the database
        if site_id is not None:
            print("\n=== SAVING RESULTS TO DATABASE ===")
            self.save_prospects_to_database(results, site_id)
        
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
        
        The search query should be specific enough to find relevant websites but general enough to return a good number of results. If a specifc category should be broken into mutiple categories, do that. The categories should only be for websites that have a blog.
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

        # Clean up the list of websites
        category_websites = self.clean_website_list(category_websites, search_term, category, self.core_phrase)

        print(f"Found {len(category_websites)} unique websites for '{category}'")
        return category_websites
    
    def clean_website_list(self, websites: List[Dict[str, Any]], search_term: str, category: str, core_phrase: str) -> List[Dict[str, Any]]:
        """
        Clean up the list of websites by:
        1. Removing major platforms that aren't good backlink prospects
        2. Using LLM to filter out websites that don't fit the category
        
        Args:
            websites: List of website dictionaries
            search_term: The search term used to find these websites
            category: The category these websites belong to
            
        Returns:
            Filtered list of website dictionaries
        """
        print(f"Cleaning up website list for category '{category}'...")
        
        # Step 1: Remove major platforms that aren't good backlink prospects
        excluded_domains = [
            "youtube.com", "youtu.be",
            "reddit.com",
            "facebook.com", "fb.com",
            "instagram.com",
            "tiktok.com",
            "twitter.com", "x.com",
            "wikipedia.org",
            "amazon.com", "amazon.", # Catches international Amazon domains
            "pinterest.com",
            "linkedin.com",
            "quora.com",
            "medium.com"
        ]
        
        # Filter out excluded domains
        filtered_websites = []
        for website in websites:
            base_url = website["url"]
            excluded = False
            
            for domain in excluded_domains:
                if domain in base_url.lower():
                    print(f"Excluding {base_url} (matches excluded domain {domain})")
                    excluded = True
                    break
            
            if not excluded:
                filtered_websites.append(website)
        
        print(f"Removed {len(websites) - len(filtered_websites)} websites from excluded domains")
        
        # Step 2: Use LLM to filter out websites that don't fit the category
        if filtered_websites:
            print(f"Using LLM to evaluate {len(filtered_websites)} websites for category fit...")
            llm_filtered_websites = []
            
            for website in filtered_websites:
                if self.is_website_relevant(website, category, core_phrase):
                    llm_filtered_websites.append(website)
                else:
                    print(f"LLM excluded: {website['url']}")
            
            print(f"LLM removed {len(filtered_websites) - len(llm_filtered_websites)} irrelevant websites")
            return llm_filtered_websites
        
        return filtered_websites
    
    def is_website_relevant(self, website: Dict[str, Any], category: str, core_phrase: str) -> bool:
        """
        Use Gemini to determine if a website is relevant to the category and would be a good backlink prospect.
        
        Args:
            website: Website dictionary with url, title, snippet
            category: The category to check relevance against
            core_phrase: The core topic of the blog
            
        Returns:
            Boolean indicating if the website is relevant
        """
        url = website["url"]
        title = website["title"]
        snippet = website["snippet"]
        
        # Skip evaluation if we don't have enough information
        if not title and not snippet:
            print(f"Skipping LLM evaluation for {url} due to insufficient information")
            return True
        
        prompt = f"""
        Website URL: {url}
        Website Title: {title}
        Website Description: {snippet}
        Category: {category}
        Core Topic: {core_phrase}
        
        Based on the information above, is this website a good candidate for reaching out about a guest post related to {core_phrase}?
        
        Consider:
        1. Is it likely that this website has a blog or content section?
        2. Is it relevant to the category "{category}" and at least somewhat semantically relevant to "{core_phrase}"?
        
        Answer with ONLY "yes" if it's a good candidate or "no" if it's not. Be generous with "yes" - only exclude websites that are clearly not a good fit.
        """
        
        try:
            # Use a cheaper/smaller Gemini model for this task
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            answer = response.text.strip().lower()
            
            # Extract just the yes/no
            if "yes" in answer:
                return True
            elif "no" in answer:
                return False
            else:
                # Default to including if the answer is ambiguous
                print(f"Ambiguous LLM response for {url}: {answer}")
                return True
        except Exception as e:
            print(f"Error evaluating website with LLM: {e}")
            # Default to including the website if there's an error
            return True

    def generate_prospects_from_plan(self, prospect_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate prospects from a prospect plan, handling deduplication across categories.
        
        Args:
            prospect_plan: A prospect plan generated by generate_prospect_plan
            
        Returns:
            A dictionary with categorized website lists and a master list of all websites
        """
        # Store core phrase as instance variable for use in other methods
        self.core_phrase = prospect_plan["core_phrase"]
        
        # Initialize the global set of all websites for deduplication
        all_websites = set()
        
        # Initialize the results structure
        results = {
            "blog_title": prospect_plan["blog_title"],
            "blog_description": prospect_plan["blog_description"],
            "core_phrase": prospect_plan["core_phrase"],
            "categories": [],
            "total_websites": []  # This will be a simple list of URLs
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
                
                # Extract just the URLs for this category
                category_urls = [website["url"] for website in websites]
                
                # Add to results
                category_result = {
                    "category": category,
                    "search_term": search_term,
                    "websites": category_urls,  # Just the URLs
                    "count": len(category_urls)
                }
                
                results["categories"].append(category_result)
                print(f"Added {len(category_urls)} websites to category '{category}'")
        
        # Create the master list of all unique websites
        results["total_websites"] = list(all_websites)
        print(f"\nTotal unique websites found across all categories: {len(results['total_websites'])}")
        
        return results

    def save_prospects_to_database(self, results: Dict[str, Any], site_id: int) -> Dict[str, Any]:
        """
        Save the prospect results to the database.
        
        Args:
            results: The results dictionary from generate_prospects_from_plan
            site_id: The ID of the site to associate with the URLs
            
        Returns:
            Dictionary with status and count of saved URLs
        """
        # Prepare the URLs for saving
        urls_to_save = []
        
        # Process each category
        for category_data in results["categories"]:
            category = category_data["category"]
            
            # Add each URL in this category
            for url in category_data["websites"]:
                urls_to_save.append({
                    "url": url,
                    "site_id": site_id,
                    "website_category": category
                })
        
        # Save to database
        if urls_to_save:
            print(f"Saving {len(urls_to_save)} URLs to database...")
            save_result = self.db_service.save_urls(urls_to_save)
            print(f"Database save result: {save_result}")
            return save_result
        else:
            print("No URLs to save to database")
            return {"status": "warning", "message": "No URLs to save", "saved_count": 0}

    def get_category_list(self, post_url: str, post_title: str) -> str:
        """
        Get the best category for a given post URL and title.
        
        Args:
            post_url: URL of the post
            post_title: Title of the post
            
        Returns:
            The best category for the post
        """
        print(f"\n=== SELECTING BEST CATEGORY FOR POST ===")
        print(f"Post URL: {post_url}")
        print(f"Post Title: {post_title}")
        
        # First, get all available categories from the database
        try:
            # Get categories from database
            categories = self.db_service.get_all_website_categories()
            
            if not categories:
                print("No categories found in database, generating categories instead...")
                categories_text = self.generate_website_categories(post_title, "")
            else:
                # Format the categories as a bulleted list for the prompt
                categories_text = "\n".join([f"- {category}" for category in categories])
                print(f"Retrieved {len(categories)} categories from database")
            
            # Create the prompt for Gemini
            prompt = f"""
            Post Title: {post_title}
            Post URL: {post_url}
            
            Available Categories:
            {categories_text}
            
            Based on the post title and URL, select ONE category from the list above that would:
            1. Be most beneficial for users reading this post
            2. Best match the specific angle or subtopic of this post
                        
            Return ONLY the name of the single best category, with no additional text or explanation.
            """
            
            # Use Gemini to select the best category
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            best_category = response.text.strip()
            
            print(f"Selected best category: {best_category}")
            return best_category
            
        except Exception as e:
            print(f"Error selecting best category: {e}")
            # Return a default category if there's an error
            return "General Websites"

def main():
    """Example usage of the ProspectGenerator."""
    # Example blog
    blog_title = "The Ultimate Guide to Rucking: Benefits, Techniques, and Gear"
    blog_description = """
    Rucking is a simple yet effective exercise that involves walking with a weighted backpack.
    This comprehensive guide covers the health benefits of rucking, proper techniques to avoid injury,
    and essential gear recommendations for beginners and experienced ruckers alike.
    """
    
    # Example site_id (replace with actual ID)
    site_id = 1
    
    generator = ProspectGenerator()
    
    # Test the get_category_list method with different posts
    print("\n=== TESTING GET_CATEGORY_LIST METHOD ===")
    
    test_posts = [
        {
            "url": "https://ruckquest.com/rucking-bone-density-strengthen-skeleton/",
            "title": "Rucking for Bone Density: Strengthen Your Skeleton One Step at a Time"
        },
        {
            "url": "https://ruckquest.com/rucking-for-cardio-guide-weighted-walking-fitness/",
            "title": "Rucking for Cardio: The Ultimate Guide to Weighted Walking for Fitness"
        },
        {
            "url": "https://ruckquest.com/ultimate-guide-footwear-rucking/",
            "title": "The Ultimate Guide to Footwear for Rucking"
        }
    ]
    
    for i, post in enumerate(test_posts, 1):
        print(f"\nTest {i}:")
        best_category = generator.get_category_list(post["url"], post["title"])
        print(f"Best category for '{post['title']}': {best_category}")
    
    # Test the get_urls_by_category method
    print("\n=== TESTING GET_URLS_BY_CATEGORY METHOD ===")
    
    test_categories = ["Fitness Blogs", "Rucking Blogs"]
    limit = 3  # Number of URLs to retrieve per category
    
    for category in test_categories:
        print(f"\nRetrieving URLs for category: {category}")
        urls = generator.db_service.get_urls_by_category(category, site_id, limit)
        
        if urls:
            print(f"Retrieved {len(urls)} URLs:")
            for i, url_data in enumerate(urls, 1):
                print(f"{i}. {url_data['url']}")
            print(f"These URLs have been moved to the back of the outreach_urls list.")
        else:
            print(f"No URLs found for category '{category}' and site ID {site_id}")
    
    # Ask if user wants to proceed with full report
    proceed = input("\nDo you want to proceed with generating the complete prospect report? (y/n): ")
    
    if proceed.lower() == 'y':
        # Use the control panel method to generate a complete report and save to database
        print("\n=== GENERATING COMPLETE PROSPECT REPORT ===")
        report = generator.generate_complete_prospect_report(blog_title, blog_description, site_id)
        
        # Display results by category
        print("\nResults by Category:")
        for i, category_data in enumerate(report["categories"], 1):
            category = category_data["category"]
            count = category_data["count"]
            print(f"\n{i}. {category} ({count} websites)")
            
            # Show top 5 websites for this category
            for j, website in enumerate(category_data["websites"][:5], 1):
                print(f"   {j}. {website}")
            
            if count > 5:
                print(f"      ... and {count - 5} more")
        
        # Print the total count
        print(f"\nTotal unique websites found: {len(report['total_websites'])}")
        
        # Print the master list of all websites
        print("\n=== MASTER LIST OF ALL WEBSITES ===")
        for i, website in enumerate(report["total_websites"], 1):
            print(f"{i}. {website}")

if __name__ == "__main__":
    main()
