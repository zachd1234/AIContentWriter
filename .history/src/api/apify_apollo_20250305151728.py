import os
from typing import Dict, Any, Optional, List
from apify_client import ApifyClient
from dotenv import load_dotenv
import time
import re
import requests

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
        # Step 1: Search for the company first using the exact URL format from the example
        company_search_url = f"https://app.apollo.io/#/companies?qOrganizationName={domain}&page=1&sortAscending=false&sortByField=recommendations_score"
        
        # Prepare the Actor input for company search
        company_run_input = {
            "url": company_search_url,
            "totalRecords": 1,  # We just need the first company
            "getWorkEmails": True,
            "getPersonalEmails": True,
            "waitForPageIdleTime": 10000  # Wait longer for page to load (10 seconds)
        }
        
        # Run the Actor and wait for it to finish
        print(f"Starting Apify scraper to find company for domain: {domain}")
        print(f"Using URL: {company_search_url}")
        company_run = self.client.actor(self.actor_id).call(run_input=company_run_input)
        
        # Get the dataset ID from the run
        company_dataset_id = company_run["defaultDatasetId"]
        company_items = list(self.client.dataset(company_dataset_id).iterate_items())
        
        if not company_items:
            print(f"No company found for domain: {domain}")
            return []
        
        # Extract organization ID from the first company result
        company = company_items[0]
        organization_id = company.get("id")
        
        if not organization_id:
            print(f"Could not find organization ID for domain: {domain}")
            return []
        
        print(f"Found company: {company.get('name')} with ID: {organization_id}")
        
        # Step 2: Search for people in the company using the organization ID
        people_search_url = f"https://app.apollo.io/#/companies?finderViewId=5b6dfc5a73f47568b2e5f11c&organizationIds[]={organization_id}&qOrganizationName={domain}&page=1&sortAscending=false&sortByField=recommendations_"
        
        # Prepare the Actor input for people search
        people_run_input = {
            "url": people_search_url,
            "totalRecords": limit,
            "getWorkEmails": True,
            "getPersonalEmails": True,
            "waitForPageIdleTime": 10000
        }
        
        # Run the Actor and wait for it to finish
        print(f"Starting Apify scraper to find people for company: {company.get('name')}")
        print(f"Using URL: {people_search_url}")
        people_run = self.client.actor(self.actor_id).call(run_input=people_run_input)
        
        # Get the dataset ID from the run
        people_dataset_id = people_run["defaultDatasetId"]
        people_items = list(self.client.dataset(people_dataset_id).iterate_items())
        
        print(f"Found {len(people_items)} people for domain: {domain}")
        
        return people_items
    
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

    def find_email_by_name(self, name: str, domain: str, company_name: str = None) -> List[str]:
        """
        Find email addresses for a person using Apollo's match API.
        
        Args:
            name: Full name of the person
            domain: Domain of the company
            company_name: Name of the company (optional)
            
        Returns:
            List of possible email addresses
        """
        api_endpoint = "https://api.apollo.io/api/v1/people/match"
        
        # Split name into first and last name
        name_parts = name.split(' ')
        first_name = name_parts[0]
        last_name = name_parts[-1] if len(name_parts) > 1 else ""
        
        # Prepare the request data
        data = {
            "api_key": os.environ.get('APOLLO_API_KEY'),
            "reveal_personal_emails": True,
            "first_name": first_name,
            "last_name": last_name,
            "domain": domain
        }
        
        # Add company name if provided
        if company_name:
            data["organization_name"] = company_name
        
        # Make the request
        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(api_endpoint, headers=headers, json=data)
            json_res = response.json()
            
            # Check if person was found
            person = json_res.get('person')
            possible_emails = []
            
            if person:
                # Get work email
                email = person.get('email')
                if email and '@' in email:
                    possible_emails.append(email)
                
                # Get personal emails
                personal_emails = person.get('personal_emails', [])
                for personal_email in personal_emails:
                    if personal_email and '@' in personal_email:
                        possible_emails.append(personal_email)
                
                return possible_emails
            
            return []
        
        except Exception as e:
            print(f"Error finding email for {name} at {domain}: {str(e)}")
            return []


# Test the Apify Apollo client
if __name__ == "__main__":
    import json
    
    # Create Apify Apollo client
    client = ApifyApolloClient()
    
    # Test domains
    test_domains = ["openai.com", "microsoft.com", "google.com"]
    
    for domain in test_domains:
        print(f"\nTesting search_people_by_domain with domain: {domain}")
        
        # Test the method directly
        people = client.search_people_by_domain(domain, limit=3)
        
        print(f"Found {len(people)} people for domain: {domain}")
        
        if people:
            # Print the first person's basic info
            person = people[0]
            print(f"First person found:")
            print(f"Name: {person.get('name', 'N/A')}")
            print(f"Title: {person.get('title', 'N/A')}")
            print(f"Company: {person.get('organization', {}).get('name', 'N/A')}")
            
            # Get email (could be in different fields)
            email = person.get('email') or person.get('workEmail') or person.get('personalEmail') or 'N/A'
            print(f"Email: {email}")
        else:
            print(f"No people found for domain: {domain}") 