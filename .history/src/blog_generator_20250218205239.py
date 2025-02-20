import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, grounding

class BlogGenerator:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Vertex AI
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        vertexai.init(project=project_id, location="us-central1")
        
        # Initialize model with grounding
        self.model = GenerativeModel("gemini-2.0-pro")
        
        # Set up Google Search grounding tool
        self.search_tool = Tool.from_google_search_retrieval(
            grounding.GoogleSearchRetrieval(
                dynamic_retrieval_config=grounding.DynamicRetrievalConfig(
                    dynamic_threshold=0.7  # Adjust threshold as needed
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
                generation_config={
                    "temperature": 0.0  # Recommended for search grounding
                }
            )
            
            return {
                "content": response.text
            }
            
        except Exception as e:
            print(f"Error generating blog post: {str(e)}")
            return None

    async def create_complete_post(self, keyword: str) -> str:
        """
        Generates a blog post and converts it to HTML in two steps
        
        Args:
            keyword (str): Main topic of the blog post
            
        Returns:
            str: Final HTML formatted blog post
        """
        # Step 1: Generate raw content
        raw_post = self.generate_blog_post(keyword)
        
        return raw_post
        
        return None

def main():
    generator = BlogGenerator()
    post = generator.generate_blog_post("Who won the super bowl in 2025?")
    
    if post:
        print("\nGenerated Blog Post:")
        print("-" * 50)
        print(post["content"])
    else:
        print("Failed to generate blog post")

if __name__ == "__main__":
    main()

