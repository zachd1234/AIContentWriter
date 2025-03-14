import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from src.api.sitemap_api import fetch_posts_from_sitemap
import json

class LinkingAgent:
    def __init__(self, base_url: str):
        # Load environment variables
        load_dotenv()
        
        self.base_url = base_url
        
        # Initialize the LLM with Gemini configuration
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            max_output_tokens=2048,
            google_api_key=os.getenv('GOOGLE_API_KEY')     
        )
        
        # Get available posts once during initialization
        self.available_posts = fetch_posts_from_sitemap(self.base_url)
        
    def suggest_internal_links(self, post_content: str) -> str:
        """Suggests internal links for a given post content"""
        try:
            # Create the prompt with the available posts and content
            prompt = f"""You are an expert content editor specializing in internal linking.
            Analyze this content and suggest 2-3 high-value internal links from our available posts.

            Available posts for linking:
            {json.dumps(self.available_posts, indent=2)}

            Content to analyze:
            {post_content}

            Guidelines for good linking:
            - Use natural, contextual anchor text (no "click here" or "read more")
            - Ensure links are topically relevant
            - Choose anchor text that appears in the original content
            - Space out links throughout the content
            - Only suggest links to posts from the available posts list

            Return a JSON array of link suggestions, each containing:
            - 'anchor_text': natural phrase from the content
            - 'target_url': matching post URL
            - 'context': surrounding paragraph or sentence
            - 'reasoning': why this link adds value
            """
            
            # Get response from LLM
            response = self.llm.invoke(prompt)
            
            try:
                # Find JSON in response
                output_text = response.content
                start = output_text.find('[')
                end = output_text.rfind(']') + 1
                
                if start == -1 or end == 0:
                    print("No JSON array found in response")
                    return []
                    
                json_str = output_text[start:end]
                suggestions = json.loads(json_str)
                
                # Display the suggestions
                print("\nAI Agent's Link Suggestions:")
                for suggestion in suggestions:
                    print(f"\nSuggested Link:")
                    print(f"→ Anchor Text: \"{suggestion['anchor_text']}\"")
                    print(f"→ Target URL: {suggestion['target_url']}")
                    print(f"→ Context: \"{suggestion['context']}\"")
                    print(f"→ Reasoning: {suggestion['reasoning']}")
                
                return suggestions
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {str(e)}")
                print(f"Raw response: {output_text}")
                return []
            
        except Exception as e:
            print(f"Error in AI analysis: {str(e)}")
            return []

    def process_content_with_links(self, content: str) -> str:
        """
        Processes the content by inserting suggested internal links.
        Returns the modified content with links inserted.
        """
        try:
            suggestions = self.suggest_internal_links(content)
            
            if not suggestions:
                return content
                
            modified_content = content
            for suggestion in suggestions:
                anchor_text = suggestion['anchor_text']
                target_url = suggestion['target_url']
                html_link = f'<a href="{target_url}">{anchor_text}</a>'
                modified_content = modified_content.replace(anchor_text, html_link)
                
            return modified_content
            
        except Exception as e:
            print(f"Error in link processing: {str(e)}")
            return content

def main():
    test_content = """
    Rucking is a fantastic way to improve your fitness and mental toughness. 
    When you start training with a weighted backpack, you'll discover new challenges 
    and benefits. The key to successful rucking is proper form and gradually 
    increasing your weight and distance.

    Choosing the right backpack is crucial for your rucking journey. You want 
    something durable and comfortable that can handle the extra weight. Many 
    people start with basic hiking backpacks, but specialized rucking packs 
    offer better weight distribution and durability.

    Training for your first ruck march requires a systematic approach. Start 
    with shorter distances and lighter weights, then progressively increase 
    both as your strength and endurance improve. Remember to maintain good 
    posture and stay hydrated throughout your ruck.
    """
    
    agent = LinkingAgent(base_url="https://ruckquest.com")
    print("AI Agent Processing Content and Inserting Links...")
    print("-" * 50)
    modified_content = agent.process_content_with_links(test_content)
    print("\nModified Content with Links:")
    print(modified_content)

if __name__ == "__main__":
    main()
