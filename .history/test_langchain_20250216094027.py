from langchain_openai import ChatOpenAI

# Initialize the ChatOpenAI model with your API key
llm = ChatOpenAI(api_key="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")

# Now you can invoke the model
response = llm.invoke("What is LangChain?")
print(response)
