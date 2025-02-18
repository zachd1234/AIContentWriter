from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-3.5-turbo")

# Chain 1: Generate Blog Outline
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
