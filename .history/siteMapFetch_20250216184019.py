import requests
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
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

def main():
    posts = fetch_posts_from_sitemap()
    if posts:
        save_posts_to_file(posts)
        # Print first few posts as example
        print("\nExample posts:")
        for post in posts[:5]:
            print(f"- {post['loc']}")
            print(f"  Last modified: {post['lastmod']}")
            print()

if __name__ == "__main__":
    main()

