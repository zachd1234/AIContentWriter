from langchain.agents import initialize_agent, Tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import GoogleSerperAPIWrapper

def test_search():
    # Initialize both APIs with their respective keys
    search = GoogleSerperAPIWrapper(serper_api_key="d5dce9e923a550cedc12015627d4d0982801c08b")
    
    # Include OpenAI API key when initializing the chat model
    llm = ChatOpenAI(
        temperature=0,
        api_key="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"  # Add your OpenAI API key here
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