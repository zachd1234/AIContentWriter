import http.client
import json
import os
from dotenv import load_dotenv
import datetime
from langchain.schema import GenerationConfig

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

def analyze_serp_results(model, results: dict) -> str:
    """
    Analyzes SERP results using the provided model
    Returns analysis as formatted text
    """
    if not results or not results.get('results'):
        return "No results to analyze"
        
    analysis_prompt = f"""Analyze these top 10 search results for "{results['keyword']}":
    {json.dumps(results['results'], indent=2)}
    
    Provide:
    1. Common themes and angles covered
    2. Content gaps or missing perspectives
    3. Types of content ranking well (guides, lists, etc.)
    4. Unique selling points of top results
    5. Key statistics or data points mentioned
    
    Format your analysis in clear, actionable bullet points."""
    
    try:
        analysis = model.generate_content(
            analysis_prompt,
            generation_config=GenerationConfig(
                temperature=0.2
            )
        )
        return analysis.text
    except Exception as e:
        print(f"Error analyzing SERP results: {str(e)}")
        return "Error in analysis"

if __name__ == "__main__":
    # Comment out the existing test_media_enhancement() call
    # test_media_enhancement()
    
    # Run our new test function instead
    test_fetch_videos_only() 