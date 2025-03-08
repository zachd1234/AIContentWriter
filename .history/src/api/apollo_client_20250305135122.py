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
            "per_page": per_page,
            # Only include people with email addresses
            "contact_email_status": ["verified"]
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
            if person.get("email"):
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
            
            # Get up to 20 people with email addresses
            people = self.search_people(organization_id=organization_id, per_page=20)
            
            # Find the best contact based on role
            best_contact = self.find_best_contact(people)
            if best_contact:
                return best_contact
        
        # If company not found or no people found in company, try direct domain search
        people = self.search_people(domain=domain, per_page=20)
        
        # Find the best contact based on role
        return self.find_best_contact(people)


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
    

def test_apollo_api():
    """
    Simple test to verify Apollo API connectivity and functionality.
    """
    # Get API key from environment
    api_key = os.environ.get("APOLLO_API_KEY")
    if not api_key:
        print("Error: APOLLO_API_KEY environment variable not set")
        return
    
    # Test domain - use the full domain without modifications
    test_domain = "openai.com"
    print(f"Testing Apollo API with domain: {test_domain}")
    
    # Test company search
    print("\n1. Testing company search...")
    company_endpoint = "https://api.apollo.io/api/v1/mixed_companies/search"
    company_payload = {
        "api_key": api_key,
        "q_organization_name": "openai",
        "page": 1,
        "per_page": 5
    }
    
    company_response = requests.post(company_endpoint, json=company_payload)
    print(f"Status code: {company_response.status_code}")
    
    if company_response.status_code == 200:
        company_data = company_response.json()
        organizations = company_data.get("organizations", [])
        print(f"Found {len(organizations)} companies")
        
        if organizations:
            company = organizations[0]
            print(f"First company: {company.get('name')}")
            company_id = company.get('id')
        else:
            company_id = None
    else:
        print(f"Error response: {company_response.text}")
        company_id = None
    
    # Test people search by domain
    print("\n2. Testing people search by domain...")
    people_endpoint = "https://api.apollo.io/api/v1/mixed_people/search"
    people_domain_payload = {
        "api_key": api_key,
        "q_organization_domains_list": [test_domain],
        "page": 1,
        "per_page": 5
    }
    
    people_domain_response = requests.post(people_endpoint, json=people_domain_payload)
    print(f"Status code: {people_domain_response.status_code}")
    
    if people_domain_response.status_code == 200:
        people_domain_data = people_domain_response.json()
        people = people_domain_data.get("people", [])
        print(f"Found {len(people)} people by domain")
        
        if people:
            person = people[0]
            print(f"First person: {person.get('name')}")
            print(f"Email: {person.get('email', 'No email')}")
    else:
        print(f"Error response: {people_domain_response.text}")

if __name__ == "__main__":
    test_apollo_api()
    
