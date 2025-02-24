import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.sitemap_api import fetch_posts_from_sitemap
import json
import re

class LinkingAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Vertex AI
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        vertexai.init(project=project_id, location="us-central1")
        
        # Initialize model
        self.model = GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")
        
    def suggest_internal_links(self, post_content: str) -> str:
        """Suggests internal links for a given post content"""
        try:
            # Create the prompt with the available posts and content
            prompt = f"""You are an expert content editor specializing in internal linking.
            Analyze this content and suggest high-value internal links from our available posts.

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
            
            # Get response from model
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.0
                )
            )
            
            try:
                # Find JSON in response
                output_text = response.text
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
            suggestions = self.suggest_internal_links(content)
            
            if not suggestions:
                return content
            
            # Use regex to replace only the first occurrence of each anchor text
            modified_content = content
            
            for suggestion in suggestions:
                anchor_text = suggestion['anchor_text']
                target_url = suggestion['target_url']
                html_link = f'<a href="{target_url}">{anchor_text}</a>'
                
                # Find first occurrence and replace it
                index = modified_content.find(anchor_text)
                if index != -1:
                    before = modified_content[:index]
                    after = modified_content[index + len(anchor_text):]
                    modified_content = before + html_link + after
                
            return modified_content
            
        except Exception as e:
            print(f"Error in link processing: {str(e)}")
            return content

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
