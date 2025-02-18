from siteMapFetch import fetch_posts_from_sitemap
import openai
from urllib.parse import urlparse
import json

def suggest_internal_links(post_content):
    """
    An AI agent that thinks through the internal linking process step by step.
    """
    try:
        # Fetch available posts
        all_posts = fetch_posts_from_sitemap()
        
        # Format posts for the agent
        posts_context = "\n".join([
            f"- {urlparse(post['loc']).path.split('/')[-1].replace('-', ' ')}: {post['loc']}"
            for post in all_posts
        ])
        
        # Create the agent prompt with step-by-step thinking
        agent_prompt = f"""
        You are an expert content editor analyzing a blog post to suggest internal links.
        
        Available posts to link to:
        {posts_context}

        Content to analyze:
        {post_content}

        Think through this step-by-step:
        1. First, read and understand the main topics and subtopics in the content
        2. Identify key concepts that could benefit from additional context
        3. Look through available posts to find relevant connections
        4. For each potential link:
           - Consider if it adds value for the reader
           - Find natural anchor text (following Google's guidelines)
           - Evaluate the surrounding context
        5. Suggest only the most valuable links (2-3 maximum)

        Format your response as JSON with this structure:
        {{
            "thought_process": [
                "Step 1: [Your analysis of the content]",
                "Step 2: [Key concepts identified]",
                "Step 3: [Relevant posts found]",
                "Step 4: [Link evaluation]",
                "Step 5: [Final selections]"
            ],
            "suggestions": [
                {{
                    "anchor_text": "natural phrase from the content",
                    "target_url": "matching post URL",
                    "context": "surrounding paragraph or sentence",
                    "reasoning": "why this link adds value"
                }}
            ]
        }}
        """

        # Get the agent's analysis
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI agent specialized in content analysis and internal linking. Think step-by-step and explain your reasoning."},
                {"role": "user", "content": agent_prompt}
            ],
            temperature=0.7
        )
        
        # Parse the agent's response
        try:
            analysis = json.loads(response.choices[0].message.content)
            
            # Display the agent's thought process
            print("\nAI Agent's Analysis:")
            for thought in analysis["thought_process"]:
                print(f"\n{thought}")
            
            print("\nSuggested Internal Links:")
            for suggestion in analysis["suggestions"]:
                print(f"\nSuggested Link:")
                print(f"→ Anchor Text: \"{suggestion['anchor_text']}\"")
                print(f"→ Target URL: {suggestion['target_url']}")
                print(f"→ Context: \"{suggestion['context']}\"")
                print(f"→ Reasoning: {suggestion['reasoning']}")
            
            return analysis["suggestions"]
            
        except json.JSONDecodeError:
            print("Error: AI response was not in the expected format")
            return []
        
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
    
    print("AI Agent Analyzing Content for Internal Linking Opportunities...")
    print("-" * 50)
    suggestions = suggest_internal_links(test_content)

if __name__ == "__main__":
    main()
