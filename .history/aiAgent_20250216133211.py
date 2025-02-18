from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType

# ✅ Step 1: Initialize LLM with OpenAI API Key
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    api_key="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"  # Replace with your actual key
)

# ✅ Step 2: Define Tools BEFORE Initializing the Agent
def calculator(expression):
    """Evaluates a mathematical expression."""
    try:
        return str(eval(expression))  # Directly evaluates math expressions
    except Exception as e:
        return str(e)

# Register the tool in LangChain
calculator_tool = Tool(
    name="Calculator",
    func=calculator,
    description="Use this tool to evaluate math expressions like '3.14 * 5 * 5'."
)

# ✅ Step 3: Initialize the Agent AFTER Defining Tools
agent = initialize_agent(
    tools=[calculator_tool],  # Attach tools properly
    llm=llm,  # Attach the LLM
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # Decision-making strategy
    verbose=True  # Print logs for debugging
)

# ✅ Step 4: Run the Agent (Test)
response = agent.invoke("What is 3.14 * 5 * 5?")
print("Response:", response)