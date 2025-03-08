import os
import requests
from typing import Dict, Any, Optional, List
import json

from dotenv import load_dotenv
load_dotenv()  # This loads the variables from .env

class ApolloSimpleClient:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Apollo API client."""
        self.api_key = api_key or os.environ.get("APOLLO_API_KEY")
        if not self.api_key:
            raise ValueError("Apollo API key not provided and APOLLO_API_KEY environment variable is not set")
        
        self.base_url = "https://api.apollo.io/api/v1"
    
    def find_person(self, first_name: str = None, last_name: str = None, 
                   domain: str = None, company_name: str = None) -> Optional[Dict[str, Any]]:
        """Find a person using Apollo's mixed_people/search endpoint."""
        endpoint = f"{self.base_url}/mixed_people/search"
        
        payload = {
            "api_key": self.api_key,
            "page": 1,
            "per_page": 10,  # Increase to get more results
            "contact_email_status": ["verified"]
        }
        
        if domain:
            payload["q_organization_domains_list"] = [domain]
        
        if first_name or last_name:
            name_parts = []
            if first_name:
                name_parts.append(first_name)
            if last_name:
                name_parts.append(last_name)
            
            if name_parts:
                payload["q_keywords"] = " ".join(name_parts)
        
        print(f"Sending request to {endpoint} with payload: {json.dumps(payload)}")
        response = requests.post(endpoint, json=payload)
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data keys: {list(data.keys())}")
            
            # Check if there's an error message
            if "error" in data:
                print(f"Error from Apollo API: {data['error']}")
                return None
            
            people = data.get("people", [])
            print(f"Found {len(people)} people")
            
            if people and len(people) > 0:
                return people[0]
        else:
            print(f"Error response: {response.text}")
        
        return None
    
    def find_first_employee_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Find the first employee at a company based on domain."""
        # Try with just the domain first
        person = self.find_person(domain=domain)
        if person:
            return person
        
        # If that doesn't work, try with common job titles
        common_titles = [
            {"first": "Marketing", "last": "Manager"},
            {"first": "Sales", "last": "Director"},
            {"first": "Chief", "last": "Officer"},
            {"first": "Content", "last": "Manager"}
        ]
        
        for title in common_titles:
            person = self.find_person(
                first_name=title["first"],
                last_name=title["last"],
                domain=domain
            )
            if person:
                return person
        
        return None

# Test the client
if __name__ == "__main__":
    client = ApolloSimpleClient()
    
    # Test domains
    test_domains = ["openai.com", "microsoft.com", "google.com"]
    
    for domain in test_domains:
        print(f"\nFinding first employee for domain: {domain}")
        person = client.find_first_employee_by_domain(domain)
        
        if person:
            print(f"Person found: {person.get('name')}")
            print(f"Title: {person.get('title', 'N/A')}")
            print(f"Email: {person.get('email', 'N/A')}")
            
            # Check for personal emails
            personal_emails = person.get("personal_emails", [])
            if personal_emails:
                print(f"Personal emails: {personal_emails}")
        else:
            print(f"No person found for domain: {domain}")