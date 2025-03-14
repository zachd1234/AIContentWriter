import os
import sys
import random

# Get the absolute path to the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

# Add the project root to Python's path if it's not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from src.api.sitemap_api import fetch_posts_from_sitemap
import json
import re

class LinkingAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Vertex AI
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        vertexai.init(project=project_id, location="us-central1")
        
        # Initialize model with the correct model name
        self.model = GenerativeModel("gemini-2.0-flash-001")
        
    def suggest_internal_links(self, post_content: str) -> str:
        """Suggests internal links for a given post content"""
        try:
            # Shuffle the available posts to eliminate position bias
            shuffled_posts = self.available_posts.copy()
            random.shuffle(shuffled_posts)
            
            # Create the prompt with the shuffled posts and content
            prompt = f"""You are an expert content editor specializing in internal linking. Analyze this content and suggest high-value internal links from our available posts.

            Available posts for linking:
            {json.dumps(shuffled_posts, indent=2)}

            Content to analyze:
            {post_content}

            Guidelines for good linking:
            - Use natural, contextual anchor text (no "click here" or "read more")
            - Ensure links are topically relevant
            - The anchor_text must exactly match the text in the content.
            - The anchor text should make sense given the post you are linking to.  
            - Space out links throughout the entire post. Don't excessively add links in one paragraph.
            - Only suggest links to posts from the available posts list

            Return a list of suggested internal links with their anchor text, target URL, context, and reasoning.
            """
            
            # Define the response schema for structured output
            response_schema = {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "anchor_text": {"type": "STRING"},
                        "target_url": {"type": "STRING"},
                        "context": {"type": "STRING"},
                        "reasoning": {"type": "STRING"}
                    },
                    "required": ["anchor_text", "target_url", "context", "reasoning"]
                }
            }
            
            # Get response from model with structured output
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )
            
            try:
                # Parse the structured output
                suggestions = json.loads(response.text)
                
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
                print(f"Raw response: {response.text}")
                return []
            
        except Exception as e:
            print(f"Error in AI analysis: {str(e)}")
            return []

    def process_content_with_links(self, content: str, base_url: str) -> str:
        """
        Processes the content by inserting suggested internal links.
        Only adds each unique link once to avoid duplicate linking.
        
        Args:
            content (str): The content to process
            base_url (str): The base URL of the website
            
        Returns:
            str: The modified content with links inserted
        """
        try:
            # Get available posts with dynamic base_url
            self.available_posts = fetch_posts_from_sitemap(base_url)
            
            # Get link suggestions
            suggestions = self.suggest_internal_links_sectioned(content)
            
            if not suggestions:
                print("No link suggestions were returned.")
                return content
            
            print(f"\nReceived {len(suggestions)} link suggestions")
            
            # Filter out duplicate anchor texts - keep only the first occurrence
            unique_anchor_texts = set()
            filtered_suggestions = []
            
            for suggestion in suggestions:
                anchor_text = suggestion['anchor_text']
                if anchor_text not in unique_anchor_texts:
                    unique_anchor_texts.add(anchor_text)
                    filtered_suggestions.append(suggestion)
                else:
                    print(f"Skipping duplicate anchor text: '{anchor_text}'")
            
            print(f"Filtered to {len(filtered_suggestions)} unique anchor texts")
            
            # Track which URLs have been used
            used_urls = set()
            
            # Find positions for each suggestion and filter out duplicates
            suggestions_with_positions = []
            for suggestion in filtered_suggestions:
                anchor_text = suggestion['anchor_text']
                target_url = suggestion['target_url']
                
                # Skip if this URL has already been used
                if target_url in used_urls:
                    print(f"Skipping: URL already used - {target_url}")
                    continue
                
                # Find the first occurrence of the anchor text
                index = content.find(anchor_text)
                if index == -1:
                    print(f"Anchor text not found: '{anchor_text}'")
                    continue
                
                # Add to our list of valid suggestions with positions
                suggestions_with_positions.append((index, suggestion))
                used_urls.add(target_url)
            
            # Sort by position in the content
            suggestions_with_positions.sort(key=lambda x: x[0])
            
            # Create a copy of the content to modify
            modified_content = content
            offset = 0  # Track how much the string has grown due to added HTML
            
            # Process each suggestion in order of appearance
            for original_index, suggestion in suggestions_with_positions:
                # Adjust index based on current offset
                adjusted_index = original_index + offset
                anchor_text = suggestion['anchor_text']
                target_url = suggestion['target_url']
                
                # Replace the anchor text with the linked version
                html_link = f'<a href="{target_url}">{anchor_text}</a>'
                
                # Update the content
                modified_content = (
                    modified_content[:adjusted_index] + 
                    html_link + 
                    modified_content[adjusted_index + len(anchor_text):]
                )
                
                # Update offset
                offset += len(html_link) - len(anchor_text)
                
                print(f"Added link: '{anchor_text}' → {target_url}")
            
            return modified_content
            
        except Exception as e:
            print(f"Error in link processing: {str(e)}")
            return content

    def suggest_internal_links_sectioned(self, post_content: str) -> list:
        """Suggests internal links by processing the post in 500-word sections"""
        try:
            print("\n🔍 Starting sectioned internal linking process...")
            
            # Shuffle the available posts to eliminate position bias
            shuffled_posts = self.available_posts.copy()
            random.shuffle(shuffled_posts)
            
            # Split content into approximately 500-word sections
            words = re.findall(r'\w+', post_content)
            section_size = 500
            sections = []
            
            # Create sections of approximately 500 words
            for i in range(0, len(words), section_size):
                section_end = min(i + section_size, len(words))
                # Find the corresponding text in the original content
                section_text = ' '.join(words[i:section_end])
                # Find the start and end positions in the original content
                start_pos = post_content.find(words[i])
                end_pos = post_content.find(words[section_end-1]) + len(words[section_end-1]) if section_end < len(words) else len(post_content)
                sections.append(post_content[start_pos:end_pos])
            
            print(f"Split content into {len(sections)} sections of ~500 words each")
            
            # First, have the AI understand all available posts for linking
            understanding_prompt = f"""You are an expert content editor specializing in internal linking.
            
            Review these available posts from our site that we can link to:
            {json.dumps(shuffled_posts, indent=2)}
            
            Your task is to understand what each post is about so you can suggest relevant links later.
            No response is needed for this step - just review the available posts.
            """
            
            # Just have the model process this information (no response needed)
            self.model.generate_content(understanding_prompt)
            
            all_suggestions = []
            already_suggested = set()  # Track URLs we've already suggested
            
            # Process each section
            for i, section in enumerate(sections):
                print(f"\nProcessing section {i+1} of {len(sections)} (~500 words)")
                
                # Create the prompt for this section
                prompt = f"""You are an expert content editor specializing in internal linking. Analyze this section of content and suggest high-value internal links from our available posts.

                Content section {i+1} of {len(sections)} to analyze:
                {section}

                Guidelines for good linking:
                - Suggest 1-3 high-quality links for this section, but only if they are truly relevant
                - Quality matches are more important than hitting the target number of links
                - Use natural, contextual anchor text (no "click here" or "read more")
                - Ensure links are topically relevant
                - The anchor_text must exactly match the text in the content
                - The anchor text should make sense given the post you are linking to
                - Only suggest links to posts from the available posts list
                """
                
                # If we have already suggested some links, tell the AI to avoid them
                if already_suggested:
                    already_suggested_list = "\n".join([f"- {url}" for url in already_suggested])
                    prompt += f"""
                    IMPORTANT: Avoid suggesting these URLs that were already suggested in previous sections:
                    {already_suggested_list}
                    """
                
                # Define the response schema for structured output
                response_schema = {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "anchor_text": {"type": "STRING"},
                            "target_url": {"type": "STRING"},
                            "context": {"type": "STRING"},
                            "reasoning": {"type": "STRING"}
                        },
                        "required": ["anchor_text", "target_url", "context", "reasoning"]
                    }
                }
                
                # Get response from model with structured output
                response = self.model.generate_content(
                    prompt,
                    generation_config=GenerationConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                        response_schema=response_schema
                    )
                )
                
                try:
                    # Parse the structured output
                    section_suggestions = json.loads(response.text)
                    
                    # Display the suggestions for this section
                    print(f"\nAI Agent's Link Suggestions for section {i+1}:")
                    for suggestion in section_suggestions:
                        print(f"\nSuggested Link:")
                        print(f"→ Anchor Text: \"{suggestion['anchor_text']}\"")
                        print(f"→ Target URL: {suggestion['target_url']}")
                        print(f"→ Context: \"{suggestion['context']}\"")
                        print(f"→ Reasoning: {suggestion['reasoning']}")
                        
                        # Add to our tracking set
                        already_suggested.add(suggestion['target_url'])
                    
                    # Add these suggestions to our cumulative list
                    all_suggestions.extend(section_suggestions)
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON response for section {i+1}: {str(e)}")
                    print(f"Raw response: {response.text}")
            
            print(f"\nTotal link suggestions across all sections: {len(all_suggestions)}")
            
            # Post-process to ensure we don't have duplicate anchor texts
            unique_suggestions = []
            seen_anchors = set()
            
            for suggestion in all_suggestions:
                anchor_text = suggestion['anchor_text'].lower()
                if anchor_text not in seen_anchors:
                    seen_anchors.add(anchor_text)
                    unique_suggestions.append(suggestion)
            
            print(f"After removing duplicate anchor texts: {len(unique_suggestions)} suggestions")
            
            return unique_suggestions
            
        except Exception as e:
            print(f"Error in sectioned internal linking: {str(e)}")
            return []

def main():
    test_content = """
<h1>How to Start Rucking: A Comprehensive Guide</h1>

<h2>What is Rucking?</h2>

<p>Rucking is simply <strong>walking with weight on your back</strong>.  It's a low-impact, full-body workout that combines cardiovascular exercise with strength training.  Unlike running, rucking is gentler on your joints, making it accessible to a wider range of fitness levels.  The added weight challenges your muscles, improving strength and endurance.  It's a versatile activity that can be done virtually anywhere – from city streets to hiking trails.</p>

<h2>Why Start Rucking?</h2>

<p>Rucking offers a multitude of benefits, making it a popular choice for fitness enthusiasts and those seeking a unique workout experience:</p>

<ul>
  <li><strong>Improved Cardiovascular Health:</strong> Rucking elevates your heart rate, improving cardiovascular fitness and reducing the risk of heart disease.</li>
  <li><strong>Increased Strength and Endurance:</strong> The added weight strengthens your legs, core, and back muscles, building both strength and endurance.</li>
  <li><strong>Calorie Burning:</strong> Rucking burns significantly more calories than regular walking, aiding in weight loss and management.</li>
  <li><strong>Enhanced Mental Well-being:</strong>  The outdoor nature of rucking and the potential for social interaction contribute to improved mental health and stress reduction.</li>
  <li><strong>Low Impact Exercise:</strong>  Unlike high-impact activities like running, rucking is easier on your joints, reducing the risk of injury.</li>
  <li><strong>Improved Posture:</strong>  The weight on your back encourages better posture and core engagement.</li>
</ul>


<h2>Getting Started: Your First Ruck</h2>

<p>Beginning your rucking journey is straightforward. <p><iframe style="aspect-ratio: 16 / 9; width: 100%" src="https://www.youtube.com/embed/-XRxXXDJOYc" title="This video provides a comprehensive guide to getting started with rucking, including choosing the right gear, planning your route, and warming up and cooling down." frameBorder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen></iframe></p>
Here's a step-by-step guide:</p>

<h3>1. Choose Your Gear:</h3>

<ul>
  <li><strong>Ruckpack:</strong> Invest in a comfortable and durable ruckpack designed for carrying weight.  Avoid using a flimsy backpack; a dedicated ruckpack provides better weight distribution and support.</li>
  <li><strong>Weight:</strong> Start with a manageable weight, such as 10-25 pounds.  You can use readily available weights like dumbbells wrapped in a towel, or specialized ruck plates. Gradually increase the weight as you get stronger.  Never exceed 1/3 of your body weight.</li>
  <li><strong>Footwear:</strong> Wear comfortable and supportive shoes or boots suitable for walking or hiking.  Good traction is essential, especially on uneven terrain.</li>
  <li><strong>Clothing:</strong> Wear moisture-wicking clothing appropriate for the weather conditions.  Layers are recommended to adjust to changing temperatures.</li>
</ul>

<h3>2. Plan Your Route:</h3>

<p>Begin with short distances, such as 1-2 miles, on relatively flat terrain.  As you gain experience, you can gradually increase the distance and challenge yourself with more varied routes.</p>

<h3>3. Warm-up and Cool-down:</h3>

<p>Always warm up before starting your ruck with light cardio, such as a brisk walk or some dynamic stretches.  Cool down afterward with static stretches to improve flexibility and reduce muscle soreness.</p>

<h3>4. Pace Yourself:</h3>

<p>Maintain a comfortable pace.  Aim for a pace of 15-20 minutes per mile initially.  If you find yourself moving slower than 20 minutes per mile, reduce the weight.  Listen to your body and take breaks when needed.</p>

<h3>5. Stay Hydrated:</h3>

<p>Carry water with you, especially during longer rucks.  Dehydration can significantly impact your performance and well-being.</p>

<h3>6. Gradual Progression:</h3>

<p>Start with 1-2 rucking sessions per week.  Gradually increase the frequency, duration, distance, and weight as your fitness improves.  Avoid increasing any of these factors by more than 10% per week.</p>


<h2>Sample Rucking Workout Plan for Beginners</h2>

<p>Here's a sample workout plan to get you started:</p>

<ul>
  <li><strong>Week 1-2:</strong> 1-2 miles, 10-15 pounds, 30-45 minutes</li>
  <li><strong>Week 3-4:</strong> 2-3 miles, 15-20 pounds, 45-60 minutes</li>
  <li><strong>Week 5-6:</strong> 3-4 miles, 20-25 pounds, 60-75 minutes</li>
</ul>

<p>Remember to adjust this plan based on your individual fitness level and progress.</p>


<h2>Key Takeaway</h2>

<p>Rucking is a highly effective and versatile full-body workout that offers numerous physical and mental health benefits.  By starting slowly, gradually increasing intensity, and listening to your body, you can safely and effectively incorporate rucking into your fitness routine and enjoy its many rewards.</p>


<h2>FAQ</h2>

<h3>Q: What type of backpack should I use for rucking?</h3>
<p>A dedicated ruckpack designed for carrying weight is recommended.  Look for features like comfortable shoulder straps, a supportive back panel, and durable construction.</p>

<h3>Q: How much weight should I start with?</h3>
<p>Begin with 10-25 pounds and gradually increase the weight as you get stronger.  Never exceed 1/3 of your body weight.</p>

<h3>Q: How often should I ruck?</h3>
<p>Start with 1-2 sessions per week and gradually increase the frequency as your fitness improves.  Avoid rucking every day.</p>

<h3>Q: What if I experience pain while rucking?</h3>
<p>Stop immediately and assess the source of the pain.  Reduce the weight, adjust your pace, or take a break.  If the pain persists, consult a healthcare professional.</p>

<h3>Q: Can I ruck in any type of weather?</h3>
<p>Adjust your clothing and gear according to the weather conditions.  Avoid rucking in extreme heat or cold without proper precautions.</p>

<h3>Q: Is rucking suitable for everyone?</h3>
<p>While generally safe, individuals with certain medical conditions should consult their doctor before starting a rucking program.</p>

<h3>Q: Where can I find rucking routes?</h3>
<p>You can ruck virtually anywhere – city streets, parks, trails, etc.  Explore your local area and find routes that suit your fitness level and preferences.</p>

    """
    
    # Updated test with dynamic base_url
    agent = LinkingAgent()
    base_url = "https://ruckquest.com"  # Test base URL
    print("AI Agent Processing Content and Inserting Links...")
    print("-" * 50)
    modified_content = agent.process_content_with_links(test_content, base_url)
    print("\nModified Content with Links:")
    print(modified_content)

if __name__ == "__main__":
    main()