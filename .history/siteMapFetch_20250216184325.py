import requests
from xml.etree import ElementTree as ET
from urllib.parse import urlparse, urljoin
import json

def fetch_posts_from_sitemap(base_url="https://ruckquest.com"):
    """
    Fetches all posts from the post sitemap of a WordPress site
    Returns a list of post URLs and their metadata
    """
    try:
        # First fetch the main sitemap
        sitemap_url = f"{base_url}/sitemap.xml"
        response = requests.get(sitemap_url)
        root = ET.fromstring(response.content)
        
        # Find the post sitemap URL
        post_sitemap_url = None
        for sitemap in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            if "post-sitemap.xml" in sitemap.text:
                post_sitemap_url = sitemap.text
                break
        
        if not post_sitemap_url:
            raise Exception("Post sitemap not found")
            
        # Fetch the post sitemap
        response = requests.get(post_sitemap_url)
        post_root = ET.fromstring(response.content)
        
        # Extract post information
        posts = []
        for url in post_root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
            post_data = {
                'loc': url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text,
                'lastmod': url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod').text if url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod') is not None else None,
            }
            posts.append(post_data)
        
        print(f"Found {len(posts)} posts in the post sitemap")
        return posts
        
    except Exception as e:
        print(f"Error fetching posts: {str(e)}")
        return []

def save_posts_to_file(posts, filename="posts.json"):
    """Saves the posts data to a JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(posts, f, indent=2)
        print(f"Saved {len(posts)} posts to {filename}")
    except Exception as e:
        print(f"Error saving posts to file: {str(e)}")

def fetch_sitemap(base_url):
    """
    Fetch and parse a sitemap.xml from a given base URL.
    
    Args:
        base_url (str): The base URL of the website (e.g., 'https://example.com')
        
    Returns:
        list: A list of URLs found in the sitemap
    """
    base_url = base_url.rstrip('/')
    sitemap_url = urljoin(base_url, '/sitemap.xml')
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; SitemapFetcher/1.0)',
            'Accept': 'application/xml,text/xml,*/*'
        }
        response = requests.get(sitemap_url, headers=headers)
        response.raise_for_status()
        
        # Debug: Print raw response and content type
        print("Content-Type:", response.headers.get('content-type'))
        print("Raw response first 500 chars:", repr(response.text[:500]))
        
        # Clean the response content more aggressively
        content = response.text.strip()
        
        # Find the XML declaration and root element
        xml_start = content.find('<?xml')
        if xml_start == -1:
            xml_start = content.find('<urlset')
        if xml_start == -1:
            xml_start = content.find('<sitemapindex')
        
        if xml_start == -1:
            raise Exception("No XML content found")
            
        # Find the end of the root element
        root_end = content.rfind('</urlset>')
        if root_end == -1:
            root_end = content.rfind('</sitemapindex>')
            
        if root_end == -1:
            raise Exception("No valid XML root element closing tag found")
            
        # Extract just the XML content
        content = content[xml_start:root_end + 10]  # +10 to include the closing tag
        
        print("\nCleaned XML:", content[:200])  # Debug: Show cleaned content
        
        # Parse the cleaned XML
        root = ET.fromstring(content)
        
        urls = []
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
        raise Exception(f"Failed to parse sitemap XML: {str(e)}\nContent preview: {content[:200]}")
    except Exception as e:
        raise Exception(f"Error processing sitemap: {str(e)}\nContent preview: {content[:200]}")

def main():
    try:
        print("Attempting to fetch sitemap from ruckquest.com...")
        urls = fetch_sitemap('https://ruckquest.com')
        print(f"\nFound {len(urls)} URLs in sitemap:")
        for url in urls:
            print(f"- {url}")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        
if __name__ == "__main__":
    main()

