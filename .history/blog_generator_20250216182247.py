from typing import List, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
import os

class BlogGenerator:
    def __init__(self):
        self.target_word_count = 1500
        # Initialize Gemini with LangChain
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-pro-exp-02-05",
            temperature=0.7,
            max_tokens=8192,
            top_p=0.8,
            top_k=40,
            google_api_key="your-actual-api-key-here"
        )

    def generate_outline(self, title: str, keyword: str, target_audience: str) -> List[str]:
        prompt = (
            f"Generate an outline for a blog post with the exact title: '{title}'\n"
            f"The blog should target the keyword '{keyword}' and satisfy the search intent "
            f"of the target audience {target_audience}\n\n"
            f"Structure requirements:\n"
            f"- First section MUST directly answer the search query/main question immediately"
        )
        
        # Note: You would implement your actual LLM call here
        # This is a placeholder for the outline generation
        outline = self._call_llm(prompt)
        return outline

    def generate_article(self, outline: List[str]) -> str:
        prompt = (
            "Now given outline, write a 1,500 word (minimum) article using the outline below. "
            "Use a neutral confident, knowledgeable, clear tone. "
            "Structure the format of the article for maximum scannability and readability. "
            "Gather inspiration from other successful, high-ranking articles on the same topic.\n"
            f"Outline:\n{self._format_outline(outline)}"
        )
        
        # Note: You would implement your actual LLM call here
        # This is a placeholder for the article generation
        article = self._call_llm(prompt)
        return article

    def _format_outline(self, outline: List[str]) -> str:
        return "\n".join([f"- {item}" for item in outline])

    def _call_llm(self, prompt: str) -> str:
        """
        Call Gemini using LangChain's integration
        
        Args:
            prompt: The input prompt for content generation
            
        Returns:
            Generated content as string
        """
        try:
            messages = [
                ("human", prompt)
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            raise Exception(f"Error calling Gemini API: {str(e)}")

    def generate_blog_post(self, title: str, keyword: str, target_audience: str) -> Dict[str, str]:
        """
        Main method to generate a complete blog post.
        
        Args:
            title: The exact title for the blog post
            keyword: The target keyword to optimize for
            target_audience: Description of the target audience
            
        Returns:
            Dictionary containing the outline and final article
        """
        outline = self.generate_outline(title, keyword, target_audience)
        article = self.generate_article(outline)
        
        return {
            "outline": outline,
            "article": article
        }

# Example usage
if __name__ == "__main__":
    generator = BlogGenerator()
    result = generator.generate_blog_post(
        title="How to Start Rucking",
        keyword="rucking",
        target_audience="beginner ruckers"
    )
    
    print("Outline:")
    print(result["outline"])
    print("\nArticle:")
    print(result["article"]) 