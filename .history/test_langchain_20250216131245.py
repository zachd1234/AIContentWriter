from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate


# Initialize the ChatOpenAI model with your API key
llm = ChatOpenAI(api_key="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")

# Now you can invoke the model
outline_prompt = PromptTemplate.from_template("Create a detailed blog outline for {keyword}.")
outline_chain = LLMChain(llm=llm, prompt=outline_prompt)

# Chain 2: Write Blog Post Based on Outline
blog_prompt = PromptTemplate.from_template(
    """Write a 1300-1900 word blog post about "{keyword}".
    Use this outline: {outline}
    Keep it at an 8th-grade reading level and return Markdown format."""
)
blog_chain = LLMChain(llm=llm, prompt=blog_prompt)

# Call the first chain
outline = outline_chain.invoke({"keyword": "AI automation"})

# Call the second chain using the outline from the first chain
blog_post = blog_chain.invoke({"keyword": "AI automation", "outline": outline})

print(blog_post)
