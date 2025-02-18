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
        'X-API-KEY': 'your_serper_api_key_here',
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
    search = GoogleSerperAPIWrapper(serper_api_key="your_serper_api_key_here")
    llm = ChatOpenAI(temperature=0.7, api_key="your_openai_api_key_here")
    
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

if __name__ == "__main__":
    test_media_enhancement() 