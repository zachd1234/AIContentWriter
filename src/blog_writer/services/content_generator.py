import os
from dotenv import load_dotenv
import vertexai
from google.generativeai import GenerativeModel
from google.generativeai.types import GenerationConfig
from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from src.api.serper_api import fetch_serp_results
import datetime

class ContentGenerator:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Vertex AI
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        vertexai.init(project=project_id, location="us-central1")
        
        # Initialize research model with grounding (for research method)
        self.research_model = GenerativeModel("gemini-1.5-flash-002")
        
        # Initialize LangChain LLM with the experimental model (for the agent)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-thinking-exp-01-21",
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

    def research_topic(self, keyword: str) -> str:
        """
        Researches a topic using the grounded search model
        """
        research_prompt = f"""Act as an expert researcher. Your task is to analyze and research "{keyword}" 
        and identify the most crucial information that someone needs to understand given their search.

        Please provide:
        1. key findings or main points
        2. important statistics or facts (with sources if available)
        3. Any critical context or background information
        4. Current relevance or implications
        5. links to authoritiative sources on the topic

        Format your response as clear, concise bullet points.
        If you find conflicting information, note it and explain the different perspectives.
        If there is limited or no reliable information available on this topic, please state that clearly instead of forcing points.

        IMPORTANT: When mentioning sources, please include the actual URLs from your search results. You have access to Google Search data, so use it to provide specific, clickable links to authoritative sources.
        """
        
        try:
            # Using the research model with grounding capabilities
            response = self.research_model.generate_content(
                research_prompt,
                generation_config=GenerationConfig(
                    temperature=0.2
                )
            )
            
            return response.text
            
        except Exception as e:
            print(f"Error conducting research: {str(e)}")
            return None

    def generate_blog_post(self, keyword: str) -> dict:
        """
        Uses LangChain agent to research and generate a blog post
        """
        try:
            agent_prompt = f"""Create a high-quality blog post about "{keyword}". Follow these steps in order:

            STEP 1: Use the Research tool to gather comprehensive information about the topic
            - Call the Research tool and analyze its findings
            - Identify key points and statistics
            - Note any authoritative sources

            STEP 2: Use the AnalyzeTopResults tool to understand the competition
            - Call the AnalyzeTopResults tool
            - Study what's currently ranking
            - Identify content gaps and opportunities

            STEP 3: Plan your content based on the research
            - Combine insights from both tools
            - Outline your unique angle
            - Plan how to fill identified content gaps

            STEP 4: Write a comprehensive blog post that:
            - Is 1300-2000 words long
            - Includes a key takeaways section
            - Has an FAQ section
            - References authoritative sources
            - Provides unique value beyond existing content

            Format the entire post in clean, semantic HTML using:
            - <h1> for the main title
            - <h2> for section headers
            - <p> for paragraphs
            - <strong> for important terms
            - <ul> and <li> for lists
            - <a href="URL">text</a> for links

            When citing sources, use proper HTML links. Example:
            According to <a href="https://harvard.edu/study">research from Harvard Medical School</a>, rucking improves cardiovascular health.

            
            Return only the HTML-formatted blog post as your final output."""

            response = self.agent.invoke({
                "input": agent_prompt
            })

            return {
                "content": response["output"],
                "keyword": keyword,
                "timestamp": datetime.datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error in content generation: {str(e)}")
            return None

def main():
    generator = ContentGenerator()
    result = generator.generate_blog_post("How much does a Phase I Environmental Site Assessment cost?")
    
    if result:
        print("\nGenerated Content:")
        print("-" * 50)
        print(result["content"])
        print("\nGenerated at:", result["timestamp"])
    else:
        print("Failed to generate content")

if __name__ == "__main__":
    main()

