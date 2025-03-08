import os
import requests
from typing import Dict, Any, Optional, List

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv(verbose=False)  # Load silently
except ImportError:
    pass  # Continue without dotenv if not available

class ApolloClient:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Apollo API client.
        
        Args:
            api_key: Apollo API key (optional, will use environment variable if not provided)
        """
        self.api_key = api_key or os.environ.get("APOLLO_API_KEY")
        if not self.api_key:
            raise ValueError("Apollo API key not provided and APOLLO_API_KEY environment variable is not set")
        
        self.base_url = "https://api.apollo.io/api/v1"
    
    def search_companies(self, domain: str, page: int = 1, per_page: int = 10) -> List[Dict[str, Any]]:
        """
        Search for companies by domain.
        
        Args:
            domain: The domain to search for (e.g., "example.com")
            page: Page number for pagination
            per_page: Number of results per page
            
        Returns:
            List of company data
        """
        endpoint = f"{self.base_url}/mixed_companies/search"
        
        payload = {
            "api_key": self.api_key,
            "q_organization_name": domain.split('.')[0],  # Use domain name without TLD as company name
            "page": page,
            "per_page": per_page
        }
        
        response = requests.post(endpoint, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("organizations", [])
        
        return []
    
    def search_people(self, domain: str = None, organization_id: str = None, page: int = 1, per_page: int = 10) -> List[Dict[str, Any]]:
        """
        Search for people associated with a domain or organization ID.
        
        Args:
            domain: The domain to search for (e.g., "example.com")
            organization_id: The Apollo organization ID
            page: Page number for pagination
            per_page: Number of results per page
            
        Returns:
            List of people data
        """
        endpoint = f"{self.base_url}/mixed_people/search"
        
        payload = {
            "api_key": self.api_key,
            "page": page,
            "per_page": per_page
        }
        
        if domain:
            payload["q_organization_domains_list"] = [domain]
        
        if organization_id:
            payload["organization_ids"] = [organization_id]
        
        response = requests.post(endpoint, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("people", [])
        
        return []
    
    def get_person_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get person data from a URL.
        
        Args:
            url: The URL to extract domain from and search
            
        Returns:
            Person data if found, None otherwise
        """
        # Extract domain from URL
        try:
            domain = url.split("//")[-1].split("/")[0]
            # Remove www. if present
            if domain.startswith("www."):
                domain = domain[4:]
        except IndexError:
            domain = url
        
        # First, try to find the company
        companies = self.search_companies(domain, per_page=1)
        
        if companies and len(companies) > 0:
            # If company found, search for people in that company
            company = companies[0]
            organization_id = company.get("id")
            
            people = self.search_people(organization_id=organization_id, per_page=1)
            
            if people and len(people) > 0:
                return people[0]
        
        # If company not found or no people found in company, try direct domain search
        people = self.search_people(domain=domain, per_page=1)
        
        if people and len(people) > 0:
            return people[0]
        
        return None


# Test the Apollo API client
if __name__ == "__main__":
    import json
    
    # Create Apollo client
    client = ApolloClient()
    
    # Test with a sample URL
    test_url = "https://openai.com"
    print(f"Testing with URL: {test_url}")
    
    # Get person from URL
    person = client.get_person_from_url(test_url)
    
    if person:
        print("\nPerson found:")
        print(f"Name: {person.get('name', 'N/A')}")
        print(f"Title: {person.get('title', 'N/A')}")
        print(f"Company: {person.get('organization_name', 'N/A')}")
        print(f"Email: {person.get('email', 'N/A')}")
        print(f"LinkedIn: {person.get('linkedin_url', 'N/A')}")
        
        # Print full response for debugging
        print("\nFull response:")
        print(json.dumps(person, indent=2))
    else:
        print("No person found for the given URL.")
    
