import http.client
import json
import os
from dotenv import load_dotenv
import datetime

def fetch_videos(query):
    """
    Fetch videos related to a query using Serper API
    Returns a list of video results with titles and URLs
    """
    load_dotenv()
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': os.getenv('SERPER_API_KEY'),
        'Content-Type': 'application/json'
    }
    
    try:
        conn.request("POST", "/videos", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        
        # Extract relevant video information
        videos = []
        if 'videos' in data:
            for video in data['videos']:
                videos.append({
                    'title': video.get('title', ''),
                    'link': video.get('link', ''),
                    'snippet': video.get('snippet', '')
                })
        return videos
    except Exception as e:
        print(f"Error fetching videos: {str(e)}")
        return []
    finally:
        conn.close()

def test_fetch_videos_only():
    """
    Simple test function to verify the fetch_videos functionality
    """
    test_queries = [
        "Tesla Cybertruck 2024",
        "SpaceX Starship launch",
        "Python programming tutorial"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: {query}")
        print("-" * 50)
        
        videos = fetch_videos(query)
        
        if videos:
            print(f"Found {len(videos)} videos:")
            for i, video in enumerate(videos, 1):
                print(f"\nVideo {i}:")
                print(f"Title: {video.get('title', 'No title')}")
                print(f"Link: {video.get('link', 'No link')}")
                print(f"Snippet: {video.get('snippet', 'No snippet')[:100]}...")  # Truncate long snippets
        else:
            print("No videos found or an error occurred")
        
        print("\n" + "="*70 + "\n")  # Separator between queries

def fetch_serp_results(keyword: str) -> dict:
    """
    Fetches top 10 search results using Serper API
    Returns dict with results and metadata
    """
    load_dotenv()
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({
        "q": keyword,
        "num": 10  # Get top 10 results
    })
    
    headers = {
        'X-API-KEY': os.getenv('SERPER_API_KEY'),
        'Content-Type': 'application/json'
    }
    
    try:
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        
        # Extract organic results
        results = []
        if 'organic' in data:
            for result in data['organic']:
                results.append({
                    'title': result.get('title', ''),
                    'link': result.get('link', ''),
                    'snippet': result.get('snippet', ''),
                    'position': result.get('position', 0)
                })
        
        return {
            "results": results,
            "keyword": keyword,
            "timestamp": datetime.datetime.now().isoformat()
        }
            
    except Exception as e:
        print(f"Error fetching SERP results: {str(e)}")
        return None
    finally:
        conn.close()

def scrape_webpage(url: str) -> str:
    """
    Scrapes a webpage using Serper API's scraping endpoint and returns the text content
    
    Args:
        url (str): The URL of the webpage to scrape
        
    Returns:
        str: The scraped text content or error message if an error occurs
    """
    load_dotenv()
    print(f"Scraping webpage: {url}")
    
    conn = http.client.HTTPSConnection("scrape.serper.dev")
    payload = json.dumps({
        "url": url
    })
    
    api_key = os.getenv('SERPER_API_KEY')
    if not api_key:
        print("Error: SERPER_API_KEY not found in environment variables")
        return "Error: SERPER_API_KEY not found in environment variables"
    
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        conn.request("POST", "/", payload, headers)
        res = conn.getresponse()
        status = res.status
        print(f"Serper API response status: {status}")
        
        if status != 200:
            error_msg = f"Error: Serper API returned status code {status}"
            print(error_msg)
            return error_msg
            
        raw_data = res.read().decode("utf-8")
        print(f"Received raw data length: {len(raw_data)} characters")
        
        data = json.loads(raw_data)
        
        # Extract just the text content from the response
        if 'text' in data:
            text_content = data['text']
            print(f"Found 'text' field with {len(text_content)} characters")
            return text_content
        elif 'content' in data:
            content = data['content']
            print(f"Found 'content' field with {len(content)} characters")
            return content
        else:
            print("No text or content field found in response")
            print(f"Response keys: {data.keys()}")
            return "No text content found in the scraped data."
    except Exception as e:
        error_msg = f"Error scraping webpage: {str(e)}"
        print(error_msg)
        return error_msg
    finally:
        conn.close()

if __name__ == "__main__":
    # Comment out the existing test_media_enhancement() call
    # test_media_enhancement()
    
    # Run our new test function instead
    print(scrape_webpage("https://www.partneresi.com/"))