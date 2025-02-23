import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, grounding, GenerationConfig
import datetime
from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from src.api.serper_api import fetch_serp_results

class ContentGenerator:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Vertex AI
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        vertexai.init(project=project_id, location="us-central1")
        
        # Initialize model with grounding
        self.model = GenerativeModel("gemini-1.5-flash-002")
        
        # Set up Google Search grounding tool with dynamic retrieval
        self.search_tool = Tool.from_google_search_retrieval(
            grounding.GoogleSearchRetrieval(
                dynamic_retrieval_config=grounding.DynamicRetrievalConfig(
                    dynamic_threshold=0.7  # Will use search for highly time-sensitive or factual queries
                )
            )
        )

        # Initialize LangChain LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            google_api_key=os.getenv('GOOGLE_API_KEY')
        )
        
        # Define tools for the agent
        research_tool = Tool(
            name="Research",
            func=self.research_topic,
            description="Researches a topic thoroughly and returns key findings, statistics, and sources"
        )
        
        serp_tool = Tool(
            name="AnalyzeTopResults",
            func=fetch_serp_results,
            description="Fetches top 10 Google search results to understand what's currently ranking"
        )

        # Initialize the agent with both tools
        self.agent = initialize_agent(
            tools=[research_tool, serp_tool],
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )

        # Define the blog post generation prompt
        self.blog_prompt = PromptTemplate(
            input_variables=["keyword", "research"],
            template="""Write a comprehensive blog post about {keyword}.

            Use this research to inform your writing:
            {research}

            Format the post in clean, semantic HTML using:
            - <h1> for the main title
            - <h2> for section headers
            - <p> for paragraphs
            - <strong> for important terms
            - <ul> and <li> for lists
            - <a href="URL">text</a> for links

            The post should:
            1. Be 1300-2000 words
            2. Include proper source citations with <a> tags
            3. Have a key takeaways section
            4. Include an FAQ section
            5. Be optimized for SEO

            Return only the HTML-formatted blog post."""
        )

    def generate_blog_post(self, keyword: str) -> dict:
        """
        Uses LangChain agent to research and generate a blog post
        """
        try:
            agent_prompt = f"""Create a high-quality blog post about "{keyword}". 
            Follow these steps:
            1. Research the topic thoroughly using the Research tool
            2. Use AnalyzeTopResults tool to see what's currently ranking
            3. Take inspiration from the top ranking sources while maintaining originality
            4. Structure and write unique content that provides value
            5. Ensure all claims are supported by research

            Take your time to plan and execute each step carefully.
            Use the tools available to gather comprehensive information."""

            response = self.agent.invoke({
                "input": agent_prompt,
                "keyword": keyword
            })

            # Generate the final blog post using the research
            final_prompt = self.blog_prompt.format(
                keyword=keyword,
                research=response['output']
            )

            final_content = self.llm.invoke(final_prompt)

            return {
                "content": final_content.content,
                "research": response['output'],
                "keyword": keyword,
                "timestamp": datetime.datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error in content generation: {str(e)}")
            return None

    def research_topic(self, keyword: str) -> dict:
        """
        Researches a topic and returns key findings and important information.
        
        Args:
            keyword (str): Topic to research
            
        Returns:
            dict: Contains key findings, important facts, and sources
        """
        research_prompt = f"""Act as an expert researcher. Your task is to analyze and research "{keyword}" 
        and identify the most crucial information that someone needs to understand given their search.

        Please provide:
        1. Key findings or main points
        2. important statistics or facts (with sources if available)
        3. Any critical context or background information
        4. Current relevance or implications
        Format your response as clear, concise bullet points.
        If you find conflicting information, note it and explain the different perspectives.
        If there is limited or no reliable information available on this topic, please state that clearly instead of forcing points.
        """
        
        try:
            response = self.model.generate_content(
                research_prompt,
                tools=[self.search_tool],
                generation_config=GenerationConfig(
                    temperature=0.2,  # Slightly higher temperature for more comprehensive research
                    max_output_tokens=1024
                )
            )
            
            return {
                "research_findings": response.text,
                "keyword": keyword,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error conducting research: {str(e)}")
            return None

def main():
    generator = ContentGenerator()
    post = generator.research_topic("How Much Weight Should I ruck With?")
    
    if post:
        print("\nGenerated Blog Post:")
        print("-" * 50)
        print(post["research_findings"])
    else:
        print("Failed to generate blog post")

if __name__ == "__main__":
    main()

