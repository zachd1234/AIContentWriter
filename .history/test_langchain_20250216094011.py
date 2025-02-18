from langchain_openai import ChatOpenAI

# Initialize the ChatOpenAI model with your API key
llm = ChatOpenAI(api_key="your_openai_api_key_here")

# Now you can invoke the model
response = llm.invoke("What is LangChain?")
print(response)
