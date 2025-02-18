from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType

# Initialize LLM
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)



# List of tools the agent can use
tools = [calculator_tool]  # Add more as needed

# Initialize the agent
agent = initialize_agent(
    tools=tools,    # Attach the tools
    llm=llm,        # Attach the LLM
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # Decision-making style
    verbose=True    # Print detailed reasoning steps
)

# Define a simple calculator tool
def calculator(expression):
    """Evaluates a mathematical expression."""
    try:
        return str(eval(expression))
    except Exception as e:
        return str(e)

# Register the tool in LangChain
calculator_tool = Tool(
    name="Calculator",
    func=calculator,
    description="Use this tool to evaluate math expressions like '3.14 * 5 * 5'."
)

response = agent.invoke("What is 3.14 * 5 * 5?")
print("Response:", response)
