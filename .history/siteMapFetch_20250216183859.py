import requests
from xml.etree import ElementTree as ET
from urllib.parse import urljoin

def fetch_sitemap(base_url):
    """
    Fetch and parse a sitemap.xml from a given base URL.
    
    Args:
        base_url (str): The base URL of the website (e.g., 'https://example.com')
        
    Returns:
        list: A list of URLs found in the sitemap
        
    Raises:
        requests.RequestException: If the sitemap cannot be fetched
        ET.ParseError: If the XML cannot be parsed
    """
    # Ensure the base URL doesn't end with a slash
    base_url = base_url.rstrip('/')
    
    # Construct the sitemap URL
    sitemap_url = urljoin(base_url, '/sitemap.xml')
    
    try:
        # Fetch the sitemap with headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; SitemapFetcher/1.0)',
            'Accept': 'application/xml,text/xml,*/*'
        }
        response = requests.get(sitemap_url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the XML
        root = ET.fromstring(response.content)
        
        # Extract URLs (handle both standard sitemaps and sitemap index files)
        urls = []
        
        # Most sitemaps use the namespace 'http://www.sitemaps.org/schemas/sitemap/0.9'
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Look for <url> elements (standard sitemap)
        for url in root.findall('.//ns:url/ns:loc', namespace):
            urls.append(url.text)
            
        # Look for <sitemap> elements (sitemap index)
        for sitemap in root.findall('.//ns:sitemap/ns:loc', namespace):
            urls.append(sitemap.text)
            
        return urls
        
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch sitemap: {str(e)}")
    except ET.ParseError as e:
        raise Exception(f"Failed to parse sitemap XML: {str(e)}")

# Test section
if __name__ == "__main__":
    try:
        urls = fetch_sitemap('https://ruckquest.com')
        print(f"Found {len(urls)} URLs in sitemap:")
        for url in urls:
            print(f"- {url}")
    except Exception as e:
        print(f"Error: {e}")

