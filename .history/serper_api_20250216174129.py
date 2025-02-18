from langchain.agents import initialize_agent, Tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import GoogleSerperAPIWrapper
import http.client
import json

def fetch_videos(query):
    """
    Fetch videos related to a query using Serper API
    Returns a list of video results with titles and URLs
    """
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': 'd5dce9e923a550cedc12015627d4d0982801c08b',
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

def enhance_post_with_media(post_content):
    """
    Analyzes a blog post and suggests relevant videos to include
    """
    # Initialize our standard tools
    search = GoogleSerperAPIWrapper(serper_api_key="d5dce9e923a550cedc12015627d4d0982801c08b")
    llm = ChatOpenAI(temperature=0.7, api_key="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")
    
    # Create tools list including our video search
    tools = [
        Tool(
            name="Search",
            func=search.run,
            description="Useful for searching the internet for current information"
        ),
        Tool(
            name="FetchVideos",
            func=fetch_videos,
            description="Searches for relevant videos based on a query"
        )
    ]
    
    # Create a prompt that instructs the agent to analyze the post and find relevant videos
    system_prompt = """You are a content enhancement specialist. Your task is to:
    1. Analyze the given blog post content
    2. Identify 2-3 key topics or points that could benefit from video content
    3. Search for relevant videos for each topic
    4. Suggest where in the post each video should be inserted
    
    Format your response as:
    Topic: [topic]
    Suggested Videos:
    - [video title] ([video link])
    Insert after: [first few words of the paragraph where video should be inserted]
    
    Keep your suggestions relevant and high-quality."""
    
    # Initialize the agent with our custom prompt
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent="zero-shot-react-description",
        verbose=True
    )
    
    # Run the agent with the post content
    response = agent.invoke({
        "input": f"Analyze this blog post and suggest relevant videos to enhance it: {post_content}"
    })
    
    return response

def test_media_enhancement():
    # Test post content
    sample_post = """
    Tesla's Latest Innovations in 2024
    
    Tesla has been making waves in the automotive industry with their recent announcements. 
    The company has unveiled new battery technology that promises to extend range while reducing costs.
    
    Their self-driving capabilities have also seen significant improvements, with new updates rolling out monthly.
    The latest version includes enhanced navigation in urban environments and better object recognition.
    
    Additionally, Tesla's energy division has been expanding rapidly, with new Megapack installations across the globe.
    These massive battery storage systems are helping stabilize power grids and enable greater adoption of renewable energy.
    """
    
    result = enhance_post_with_media(sample_post)
    print(result)

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

if __name__ == "__main__":
    # Comment out the existing test_media_enhancement() call
    # test_media_enhancement()
    
    # Run our new test function instead
    test_fetch_videos_only() 