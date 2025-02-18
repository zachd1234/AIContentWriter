from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from siteMapFetch import fetch_posts_from_sitemap
from urllib.parse import urlparse
import json

class LinkingAgent:
    def __init__(self):
        # Initialize the LLM with the same configuration as your other services
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            api_key="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"
        )
        
        # Create a tool for fetching posts
        fetch_posts_tool = Tool(
            name="FetchPosts",
            func=fetch_posts_from_sitemap,
            description="Fetches all available blog posts from the sitemap"
        )
        
        # Initialize the agent
        self.agent = initialize_agent(
            tools=[fetch_posts_tool],
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )
        
        # Set up the system message
        self.system_message = """You are an expert content editor specializing in internal linking.
When analyzing content:
1. Read and understand the main topics and subtopics
2. Identify key concepts that could benefit from additional context
3. Look through available posts to find relevant connections
4. For each potential link:
   - Consider if it adds value for the reader
   - Find natural anchor text (following Google's guidelines)
   - Evaluate the surrounding context
5. Suggest only the most valuable links (2-3 maximum)

Return a JSON array of link suggestions, each containing:
- 'anchor_text': natural phrase from the content
- 'target_url': matching post URL
- 'context': surrounding paragraph or sentence
- 'reasoning': why this link adds value

Follow Google's guidelines for good anchor text:
- Make it descriptive and concise
- Avoid generic terms like "click here" or "read more"
- Ensure it's relevant to both source and target content
- Don't stuff keywords
- Space out links naturally in the content"""

    def suggest_internal_links(self, post_content: str) -> str:
        """Suggests internal links for a given post content"""
        try:
            # Create the prompt for the agent
            prompt = f"""
            {self.system_message}
            
            Content to analyze:
            {post_content}
            
            Analyze this content and suggest internal links following the guidelines.
            Return your suggestions as a JSON array.
            """
            
            # Run the agent
            response = self.agent.invoke({"input": prompt})
            
            # Parse and format the suggestions
            suggestions = json.loads(response["output"])
            
            # Display the suggestions
            print("\nAI Agent's Link Suggestions:")
            for suggestion in suggestions:
                print(f"\nSuggested Link:")
                print(f"→ Anchor Text: \"{suggestion['anchor_text']}\"")
                print(f"→ Target URL: {suggestion['target_url']}")
                print(f"→ Context: \"{suggestion['context']}\"")
                print(f"→ Reasoning: {suggestion['reasoning']}")
            
            return suggestions
            
        except Exception as e:
            print(f"Error in AI agent analysis: {str(e)}")
            return []

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
    
    agent = LinkingAgent()
    print("AI Agent Analyzing Content for Internal Linking Opportunities...")
    print("-" * 50)
    suggestions = agent.suggest_internal_links(test_content)

if __name__ == "__main__":
    main()
