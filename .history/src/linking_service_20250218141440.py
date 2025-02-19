from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from siteMapFetch import fetch_posts_from_sitemap
from urllib.parse import urlparse
import json

class LinkingAgent:
    def __init__(self, base_url: str):
        # Store base_url
        self.base_url = base_url
        
        # Initialize the LLM with Gemini configuration
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            max_output_tokens=2048,  # Added to prevent truncation
            google_api_key="AIzaSyAgBew-UTCDpKGAb1qidbs0CrfC9nKU9ME"        )
        
        # Create a wrapper function to handle the tool input properly
        def fetch_posts_wrapper(input_str):
            # Always use the base_url from the class instance
            return fetch_posts_from_sitemap(self.base_url)
        
        # Create a tool for fetching posts with simpler description
        fetch_posts_tool = Tool(
            name="FetchPosts",
            func=fetch_posts_wrapper,
            description="Fetches all available blog posts from the sitemap. No parameters needed."
        )
        
        # Initialize the agent with a longer timeout
        self.agent = initialize_agent(
            tools=[fetch_posts_tool],
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,  # Limit number of tool uses
            early_stopping_method="generate"  # Better handling of stopping conditions
        )
        
        # Updated system message with clearer instructions
        self.system_message = """You are an expert content editor specializing in internal linking.
Your task is to analyze content and suggest relevant internal links. Follow these steps exactly:

1. First use the FetchPosts tool to get all available posts
2. After receiving the posts list, compare the provided content's topics with the available posts to find relevant matches
4. Suggest 2-3 high-value internal links that would benefit readers

For each suggested link, you must provide a JSON object with:
{
    "anchor_text": "exact phrase from the content to use as anchor",
    "target_url": "full URL from the fetched posts",
    "context": "the full sentence or paragraph containing the anchor text",
    "reasoning": "brief explanation of why this link adds value"
}

Return a JSON array of link suggestions, each containing:
- 'anchor_text': natural phrase from the content
- 'target_url': matching post URL
- 'context': surrounding paragraph or sentence
- 'reasoning': why this link adds value

Guidelines for good linking:
- Use natural, contextual anchor text (no "click here" or "read more")
- Ensure links are topically relevant
- Choose anchor text that appears in the original content
- Space out links throughout the content
- Only suggest links to posts that were returned by FetchPosts

Return your response as a JSON array of link suggestions, even if you only find one or no suitable links."""

    def suggest_internal_links(self, post_content: str) -> str:
        """Suggests internal links for a given post content"""
        try:
            # Create the prompt for the agent
            prompt = f"""
            {self.system_message}
            
            Base URL for internal links: {self.base_url}
            
            Content to analyze:
            {post_content}
            
            First use FetchPosts to get the available posts, then analyze the provided content and suggest relevant internal links.
            Remember to return your suggestions as a JSON array following the exact format specified above.
            """
            
            # Run the agent with a timeout
            response = self.agent.invoke(
                {"input": prompt},
                {"timeout": 60}  # 60 second timeout
            )
            
            # Add error handling and validation
            if not response or "output" not in response:
                print("No valid response from agent")
                return []
                
            # Try to extract JSON from the response
            try:
                # The response might contain additional text, so try to find JSON array
                output_text = response["output"]
                # Find the first [ and last ] to extract the JSON array
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
            print(f"Error in AI agent analysis: {str(e)}")
            return []

    def process_content_with_links(self, content: str) -> str:
        """
        Processes the content by inserting suggested internal links.
        Returns the modified content with links inserted.
        """
        try:
            # Get link suggestions
            suggestions = self.suggest_internal_links(content)
            
            # If no suggestions, return original content
            if not suggestions:
                return content
                
            # Process each suggestion and insert links
            modified_content = content
            for suggestion in suggestions:
                anchor_text = suggestion['anchor_text']
                target_url = suggestion['target_url']
                
                # Create the HTML link
                html_link = f'<a href="{target_url}">{anchor_text}</a>'
                
                # Replace the anchor text with the HTML link
                modified_content = modified_content.replace(anchor_text, html_link)
                
            return modified_content
        except Exception as e:
            print(f"Error in link processing: {str(e)}")
            return content  # Return original content if there's an error

def main():
    # Sample blog post content for testing
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
    
    agent = LinkingAgent(base_url="https://ruckquest.com")  # Replace with your actual domain
    print("AI Agent Processing Content and Inserting Links...")
    print("-" * 50)
    modified_content = agent.process_content_with_links(test_content)
    print("\nModified Content with Links:")
    print(modified_content)

if __name__ == "__main__":
    main()
