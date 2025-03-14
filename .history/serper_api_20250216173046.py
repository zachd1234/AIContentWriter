from langchain.agents import initialize_agent, Tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import GoogleSerperAPIWrapper

def test_search():
    # Initialize both APIs with their respective keys
    search = GoogleSerperAPIWrapper(serper_api_key="your_serper_api_key_here")
    
    # Include OpenAI API key when initializing the chat model
    llm = ChatOpenAI(
        temperature=0,
        api_key="your_openai_api_key_here"  # Add your OpenAI API key here
    )
    
    # Create tools list
    tools = [
        Tool(
            name="Search",
            func=search.run,
            description="Useful for searching the internet for current information"
        )
    ]
    
    # Initialize the agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent="zero-shot-react-description",
        verbose=True
    )
    
    # Test query
    query = "What are the latest developments with Tesla?"
    response = agent.invoke({"input": query})
    print(response)

if __name__ == "__main__":
    test_search() 