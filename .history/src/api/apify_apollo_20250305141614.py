import os
from typing import Dict, Any, Optional, List
from apify_client import ApifyClient
from dotenv import load_dotenv
import time
import re

# Load environment variables
load_dotenv(verbose=False)

class ApifyApolloClient:
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the Apify Apollo.io scraper client.
        
        Args:
            api_token: Apify API token (optional, will use environment variable if not provided)
        """
        self.api_token = api_token or os.environ.get("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("Apify API token not provided and APIFY_API_TOKEN environment variable is not set")
        
        self.client = ApifyClient(self.api_token)
        self.actor_id = "code_crafter~apollo-io-scraper"
    
    def extract_domain_from_url(self, url: str) -> str:
        """
        Extract domain from URL.
        
        Args:
            url: The URL to extract domain from
            
        Returns:
            Domain name
        """
        # Extract domain using regex to handle various URL formats
        domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', url)
        if domain_match:
            return domain_match.group(1)
        return url
    
    def search_people_by_domain(self, domain: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for people associated with a domain using Apify's Apollo.io scraper.
        
        Args:
            domain: The domain to search for (e.g., "example.com")
            limit: Maximum number of people to return
            
        Returns:
            List of people data
        """
        # Create a search URL for Apollo.io
        search_url = f"https://app.apollo.io/#/people?q_organization_domains={domain}"
        
        # Prepare the Actor input
        run_input = {
            "url": search_url,
            "totalRecords": limit,  # Limit the number of records to scrape
            "getWorkEmails": True,
            "getPersonalEmails": True,
        }
        
        # Run the Actor and wait for it to finish
        print(f"Starting Apify scraper for domain: {domain}")
        run = self.client.actor(self.actor_id).call(run_input=run_input)
        
        # Get the dataset ID from the run
        dataset_id = run["defaultDatasetId"]
        print(f"Scraping completed. Dataset ID: {dataset_id}")
        
        # Fetch items from the dataset
        items = list(self.client.dataset(dataset_id).iterate_items())
        print(f"Found {len(items)} people")
        
        return items
    
    def find_best_contact(self, people: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the best contact from a list of people based on role preference.
        
        Args:
            people: List of people data
            
        Returns:
            Best contact data if found, None otherwise
        """
        if not people:
            return None
        
        # Define role keywords in order of preference
        role_preferences = [
            ["editor", "blog", "content", "writer"],
            ["marketing", "communications", "pr", "public relations"],
            ["seo", "growth", "digital"],
            ["manager", "director", "head", "lead"]
        ]
        
        # First, try to find someone with a preferred role
        for role_keywords in role_preferences:
            for person in people:
                title = person.get("title", "").lower()
                if any(keyword in title for keyword in role_keywords):
                    return person
        
        # If no one with preferred roles, return the first person with an email
        for person in people:
            if person.get("email") or person.get("workEmail") or person.get("personalEmail"):
                return person
        
        # If no one has an email, return the first person
        return people[0] if people else None
    
    def get_person_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get person data from a URL.
        
        Args:
            url: The URL to extract domain from and search
            
        Returns:
            Person data if found, None otherwise
        """
        # Extract domain from URL
        domain = self.extract_domain_from_url(url)
        print(f"Extracted domain: {domain}")
        
        # Search for people by domain
        people = self.search_people_by_domain(domain)
        
        # Find the best contact based on role
        return self.find_best_contact(people)


# Test the Apify Apollo client
if __name__ == "__main__":
    import json
    
    # Create Apify Apollo client
    client = ApifyApolloClient()
    
    # Test with a sample URL
    test_url = "https://openai.com"
    print(f"Testing with URL: {test_url}")
    
    # Get person from URL
    person = client.get_person_from_url(test_url)
    
    if person:
        print("\nPerson found:")
        print(f"Name: {person.get('name', 'N/A')}")
        print(f"Title: {person.get('title', 'N/A')}")
        print(f"Company: {person.get('organization', {}).get('name', 'N/A')}")
        
        # Get email (could be in different fields depending on Apify's output)
        email = person.get('email') or person.get('workEmail') or person.get('personalEmail') or 'N/A'
        print(f"Email: {email}")
        
        print(f"LinkedIn: {person.get('linkedInUrl', 'N/A')}")
        
        # Print full response for debugging
        print("\nFull response:")
        print(json.dumps(person, indent=2))
    else:
        print("No person found for the given URL.") 