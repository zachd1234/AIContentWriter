from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain_community.utilities import GoogleSerperAPIWrapper
import os

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    api_key="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"
)

# Initialize Serper
search = GoogleSerperAPIWrapper(
    serper_api_key="89a3550fc6f6fde0f5874c7d5fc3b9e0e8b0f751"
)

# Create the search tool
search_tool = Tool(
    name="Search",
    func=search.run,
    description="Search the web for current information about a topic. Input should be a search query."
)

# Initialize the agent with the search tool
agent = initialize_agent(
    tools=[search_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

def test_search():
    """Test the search functionality"""
    query = "What is the latest news about Tesla?"
    response = agent.invoke({"input": query})
    print("Response:", response)

if __name__ == "__main__":
    test_search() 