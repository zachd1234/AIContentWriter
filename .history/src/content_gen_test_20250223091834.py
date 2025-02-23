import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, grounding, GenerationConfig
import datetime

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

    def generate_blog_post(self, keyword: str) -> dict:
        """
        Generates a complete blog post optimized for the given keyword in HTML format
        """
        prompt = f"""You are an expert on the topic and your goal is to write a blog post that ranks 1st on Google for the keyword: "{keyword}"

        Write a 1300-2000 word blog post for this keyword. Include a key takeaway and FAQ section.
        Format the entire post in clean, semantic HTML using:
        - <h1> for the main title
        - <h2> for section headers
        - <p> for paragraphs
        - <strong> for important terms
        - <ul> and <li> for lists
        - <a href="URL">text</a> for links

        If you reference a source in the content, add an external link using proper <a> tags.
        Example: According to <a href="https://harvard.edu/study">research from Harvard Medical School</a>, rucking improves cardiovascular health.

        Return only the HTML-formatted blog post content.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                tools=[self.search_tool],
                generation_config=GenerationConfig(
                    temperature=0.0
                )
            )
            
            return {
                "content": response.text
            }
            
        except Exception as e:
            print(f"Error generating blog post: {str(e)}")
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
        1. key findings or main points
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
    post = generator.research_topic("Who won the super bowl in 2025?")
    
    if post:
        print("\nGenerated Blog Post:")
        print("-" * 50)
        print(post["content"])
    else:
        print("Failed to generate blog post")

if __name__ == "__main__":
    main()

