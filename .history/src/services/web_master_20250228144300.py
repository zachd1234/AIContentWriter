import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from typing import Dict, List, Optional
import json
import re

class WebMaster:
    """
    WebMaster class for handling web content operations.
    Currently supports editing posts to fix HTML formatting issues.
    """
    
    def __init__(self, base_url: Optional[str] = None):
        load_dotenv()
        self.base_url = base_url
        self.GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
        
        # Initialize Gemini for HTML analysis
        self.llm = ChatGoogleGenerativeAI(
            model="models/gemini-2.0-flash-thinking-exp-01-21",
            temperature=0.2,
            google_api_key=self.GOOGLE_API_KEY
        )
        
        # Configure genai with API key
        genai.configure(api_key=self.GOOGLE_API_KEY)
        
    def edit_post(self, blog_post: str) -> str:
        """
        Analyzes a blog post for HTML formatting issues and fixes them.
        
        Args:
            blog_post (str): The HTML content of the blog post
            
        Returns:
            str: The blog post with fixed HTML formatting
        """
        try:
            print("\n🔍 Starting HTML formatting analysis...")
            print(f"Blog post length: {len(blog_post)} characters")
            
            # Define the response schema for structured output
            response_schema = {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "issue": {"type": "STRING"},
                        "originalHtml": {"type": "STRING"},
                        "fixedHtml": {"type": "STRING"},
                        "explanation": {"type": "STRING"}
                    },
                    "required": ["issue", "originalHtml", "fixedHtml", "explanation"]
                }
            }
            
            # Create the prompt for HTML analysis
            prompt = f"""
            You are an expert HTML formatter and web developer. Analyze the following blog post HTML content 
            and identify any formatting issues that need to be fixed.
            
            Here's the blog post to analyze:
            {blog_post}
            
            INSTRUCTIONS:
            1. Carefully examine the HTML for formatting problems such as:
               - Unclosed tags
               - Improperly nested elements
               - Missing paragraph tags
               - Inconsistent heading hierarchy
               - Improper list formatting
               - Broken or malformed links
               - Improper spacing or line breaks
               - Any other HTML syntax errors
            
            2. For each issue you find, provide:
               - A description of the issue
               - The exact problematic HTML snippet (keep it short and precise)
               - The corrected HTML snippet
               - A brief explanation of the fix
            
            3. Only identify real HTML formatting issues - do not change the content or style choices
               unless they represent actual HTML syntax problems.
            
            4. If you find no issues, return an empty array.
            
            RETURN FORMAT:
            Return a JSON array of objects, each representing one issue found:
            [
              {{
                "issue": "Brief description of the issue",
                "originalHtml": "The exact problematic HTML snippet",
                "fixedHtml": "The corrected HTML snippet",
                "explanation": "Brief explanation of what was fixed and why"
              }}
            ]
            """
            
            # Create the model with structured output configuration
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-001",
                generation_config={
                    "temperature": 0.1,
                }
            )
            
            # Generate structured response
            response = model.generate_content(
                contents=prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": response_schema
                }
            )
            
            # Get the structured output
            structured_output = response.text
            print(f"📋 Analysis results: {structured_output[:200]}...")
            
            # Parse the JSON response
            formatting_issues = json.loads(structured_output)
            
            # If no issues found, return the original post
            if not formatting_issues:
                print("✅ No HTML formatting issues found.")
                return blog_post
                
            # Apply fixes to the blog post
            fixed_post = blog_post
            print(f"\n🔧 Found {len(formatting_issues)} HTML formatting issues to fix:")
            
            for i, issue in enumerate(formatting_issues, 1):
                original_html = issue["originalHtml"]
                fixed_html = issue["fixedHtml"]
                
                # Skip if original and fixed are identical
                if original_html == fixed_html:
                    print(f"  ⚠️ Issue #{i}: No change needed for '{original_html[:30]}...'")
                    continue
                    
                # Check if the original HTML exists in the post
                if original_html in fixed_post:
                    # Replace the original HTML with the fixed version
                    fixed_post = fixed_post.replace(original_html, fixed_html)
                    print(f"  ✅ Issue #{i} fixed: {issue['issue']}")
                else:
                    # Try a more flexible approach - look for similar text
                    print(f"  ⚠️ Issue #{i}: Could not find exact match for '{original_html[:30]}...'")
                    
                    # Try to find the closest match
                    # Escape special regex characters but keep wildcards for flexibility
                    pattern = re.escape(original_html).replace('\\*', '.*?')
                    matches = re.findall(pattern, fixed_post)
                    
                    if matches:
                        for match in matches:
                            fixed_post = fixed_post.replace(match, fixed_html)
                        print(f"  ✅ Issue #{i} fixed using pattern matching: {issue['issue']}")
                    else:
                        print(f"  ❌ Issue #{i}: Could not find a match for '{original_html[:30]}...'")
            
            return fixed_post
            
        except Exception as e:
            print(f"\n❌ Error in edit_post: {str(e)}")
            return blog_post  # Return original post if there's an error

def main():
    """
    Demonstrates the WebMaster functionality with a sample blog post.
    """
    # Sample blog post with some HTML formatting issues
    sample_post = """<p>Rucking, the act of walking or hiking with a weighted backpack, has evolved from <a href="https://ruckquest.com/ultimate-guide-rucking-army-training-beginners/">military training</a> to a popular fitness activity. But beyond solo rucks and fitness routines, a competitive scene is emerging: <strong>rucking competitions</strong>. These events test your endurance, strength, and mental fortitude in unique and challenging ways. If you're looking to push your limits and experience the camaraderie of the rucking community, understanding rucking competitions is your first step. This guide will provide a comprehensive overview of this growing fitness trend.</p>

    <h2>What are Rucking Competitions?</h2>
    <p>At its core, a rucking competition involves participants traversing a set distance, often over varied terrain, while carrying a weighted rucksack (ruck). Unlike traditional races focused solely on speed, rucking competitions emphasize endurance under load. The weight, distance, and specific challenges can vary significantly depending on the event, making for a diverse and engaging competitive landscape.  These competitions are not just about physical strength; they demand mental resilience, strategic pacing, and the ability to endure discomfort for extended periods.</p>

    <h2>The Origins of Rucking and its Competitive Evolution</h2>
    <p>Rucking's roots are firmly planted in <strong>military training</strong>. For decades, soldiers have rucked as a fundamental part of their conditioning, preparing them for the demands of carrying gear over long distances in challenging environments. This military heritage instills a sense of discipline and toughness that carries over into civilian rucking. As rucking gained popularity as a fitness activity outside the military, it was natural for a competitive element to emerge.  People started seeking new ways to challenge themselves and test their rucking prowess against others. This organic growth, driven by the rucking community, has led to the diverse range of competitions we see today.</p>

    <h2>Types of Rucking Competitions</h2>
    <p>Rucking competitions are far from monolithic.  Their beauty lies in their variety, offering something for almost every fitness level and competitive spirit. Here are some common types and variations:</p>

    <ul>
        <li><strong>Distance-Based Rucks:</strong> These are perhaps the most straightforward, focusing on completing a set distance (e.g., 5k, 10k, half marathon, marathon distances and beyond) with a prescribed weight. The fastest to finish wins.</li>
        <li><strong>Endurance Challenges:</strong> These competitions often extend beyond typical race distances, sometimes lasting for 12, 24 hours or even multiple days. They test the limits of physical and mental endurance, often incorporating sleep deprivation and additional tasks beyond just rucking.</li>
        <li><strong>Team Rucking Events:</strong>  Camaraderie is a big part of rucking, and team events emphasize this. Teams work together to complete a course, often with shared weight or specific team-based challenges.  These events highlight cooperation and mutual support.</li>
        <li><strong>GORUCK Challenges:</strong> <a href="https://www.goruck.com/pages/goruck-events?srsltid=AfmBOooySFQbzwJlF2hnlojsDHsqAW-rzMTLfo29kFxLTqcvG2vpLAau">GORUCK</a> is a prominent organization in the rucking world, known for its challenging events led by Special Forces veterans. GORUCK events vary in duration and intensity, often incorporating elements of military-style training and team-based missions.</li>
        <li><strong>Weight Variations:</strong>  Weight requirements differ significantly. Some competitions have strict weight classes (e.g., based on body weight or gender), while others might have a single standard weight. Some events even allow for variable weight, adding a strategic element to weight management during the ruck.</li>
        <li><strong>Terrain and Obstacles:</strong>  Rucking competitions can take place on roads, trails, mountains, or even urban environments. Some incorporate obstacles like walls, carries, or crawls, adding to the physical and mental challenge.</li>
    </ul>

    <p>Organizations like <a href="https://ruckevents.com/">Ruck Events</a> serve as directories to discover various rucking competitions, showcasing the breadth of events available. You can also find events organized by groups like <a href="https://www.rucknrun.org/events">Ruck 'N' Run®</a>, which often have a charitable or veteran-supporting focus.</p>

    <h2>Benefits of Participating in Rucking Competitions</h2>
    <p>Why participate in a rucking competition? The reasons are multifaceted, appealing to a range of motivations:</p>

    <ul>
        <li><strong>Enhanced Physical Fitness:</strong> Rucking is a fantastic full-body workout, improving <strong><a href="https://ruckquest.com/10-benefits-of-rucking-1-hour-daily/">cardiovascular endurance</a></strong>, <strong><a href="https://ruckquest.com/functional-fitness-best-exercises/">muscular strength</a></strong>, and <strong><a href="https://ruckquest.com/rucking-for-weight-loss/">calorie burning</a></strong>. Competing pushes you to train harder and achieve a higher level of fitness.</li>
        <li><strong>Mental Toughness and Resilience:</strong>  Rucking, especially in a competitive setting, is as much a mental challenge as a physical one. Overcoming discomfort, pushing through fatigue, and maintaining focus build incredible mental resilience that translates to other aspects of life.</li>
        <li><strong>Community and Camaraderie:</strong> The rucking community is known for its supportive and encouraging nature. Rucking competitions provide a platform to connect with like-minded individuals, forge bonds through shared challenges, and experience a unique sense of camaraderie.</li>
        <li><strong>Goal Setting and Achievement:</strong> Training for and completing a rucking competition provides a tangible goal to work towards. Crossing the finish line is a deeply satisfying achievement, boosting confidence and self-esteem.</li>
        <li><strong>Unique Challenge:</strong>  Rucking competitions offer a different kind of challenge compared to traditional running races or gym workouts. They test functional fitness and grit in a way that's deeply rewarding.</li>
    </ul>

    <h2>Getting Started: Training for Your First Rucking Competition</h2>
    <p>Ready to take on a rucking competition? Here's how to get started with your training:</p>

    <ol>
        
[embed]https://www.youtube.com/watch?v=HuHlLziKhBM&pp=ygUJI3JydWNraW5n[/embed]

<li><strong>Start with Rucking Basics:</strong> If you're new to rucking, begin with shorter distances and lighter weights. Gradually increase both as your body adapts. Focus on proper form to prevent injuries.</li>
        <li><strong>Build a Training Plan:</strong>  Develop a structured training plan that includes regular rucking sessions, <a href="https://ruckquest.com/functional-fitness-best-exercises/">strength training</a>, and rest days. Tailor your plan to the specific demands of the competition you're targeting (distance, weight, terrain).</li>
        <li><strong>Progressive Overload:</strong>  Gradually increase the weight, distance, or intensity of your rucks over time to continually challenge yourself and improve your fitness.</li>
        <li><strong>Strength Training:</strong> Incorporate strength training exercises that complement rucking, focusing on legs, core, and back muscles. Squats, lunges, deadlifts, and core work are particularly beneficial.</li>
        <li><strong>Practice with Competition Weight:</strong>  As you get closer to the competition, train with the weight you'll be carrying during the event to get your body accustomed to the load.</li>
        <li><strong>Terrain-Specific Training:</strong> If the competition involves trails or hills, incorporate similar terrain into your training rucks.</li>
        <li><strong>Nutrition and Hydration:</strong>  Pay attention to your nutrition and <a href="https://ruckquest.com/essential-rucking-tips-beginners/">hydration</a>, especially during longer training rucks. Practice your fueling strategy for race day.</li>
        <li><strong>Gear Up:</strong> Invest in a <a href="https://ruckquest.com/top-5-affordable-rucking-backpacks/">quality rucksack</a> and <a href="https://ruckquest.com/top-10-best-rucking-boots-comfort-durability/">comfortable footwear</a>. Test your gear during training to ensure it's suitable for competition conditions.</li>
        <li><strong>Listen to Your Body:</strong> Rest and recovery are crucial. Don't push through pain. Allow your body adequate time to recover to prevent injuries and optimize performance.</li>
    </ol>

    <h2>What to Expect on Competition Day</h2>
    <p>Stepping up to the starting line of your first rucking competition can be both exciting and nerve-wracking. Here's a glimpse of what you can expect:</p>

    <ul>
        <li><strong>Pre-Race Briefing:</strong>  Event organizers will typically provide a briefing outlining the course, rules, safety guidelines, and any last-minute instructions. Pay close attention to this.</li>
        <li><strong>The Start:</strong> The atmosphere at the start line is usually charged with energy and anticipation.  Expect a mix of seasoned ruckers and first-timers, all united by the challenge ahead.</li>
        <li><strong>The Ruck:</strong> During the competition, you'll be focused on maintaining your pace, managing your energy, and navigating the course. Expect moments of discomfort and fatigue, but also moments of accomplishment as you tick off milestones.</li>
        <li><strong>Aid Stations:</strong> Many longer rucking competitions have aid stations along the course, providing water, snacks, and sometimes medical support. Utilize these to refuel and hydrate.</li>
        <li><strong>Community Support:</strong>  Encouragement from fellow participants and volunteers is a hallmark of rucking events. Don't hesitate to offer or accept support.</li>
        <li><strong>The Finish Line:</strong> Crossing the finish line is an incredible feeling of accomplishment.  Expect cheers, high-fives, and a well-deserved sense of pride in what you've achieved.</li>
        <li><strong>Post-Race Recovery:</strong>  Prioritize recovery after the competition. Hydrate, refuel, stretch, and allow your body time to rest and repair.</li>
    </ul>

    <h2>Finding Rucking Competitions Near You</h2>
    <p>Interested in finding a rucking competition to participate in? Here are some resources:</p>

    <ul>
        <li><strong>Ruck Event Directories:</strong> Websites like <a href="https://ruckevents.com/">Ruck Events</a> and others compile lists of rucking events across different regions.</li>
        <li><strong>GORUCK Website:</strong> <a href="https://www.goruck.com/pages/find-an-event?srsltid=AfmBOoooq3I607lWSwYeKIkgpduijhhHerJ8zIh43W30ymTt3UktquE5">GORUCK Events</a> are widely available and offer various challenge levels.</li>
        <li><strong>Local Fitness Communities:</strong> Check with local gyms, CrossFit boxes, and outdoor fitness groups, as they may organize or participate in rucking events.</li>
        <li><strong>Race Calendars:</strong> Some general race calendars may include rucking events alongside running and other endurance races. Search for "rucking" or "ruck march" in online race calendars.</li>
        <li><strong>Social Media and Forums:</strong>  Rucking communities on social media (Facebook groups, Reddit <a href="https://www.reddit.com/r/Goruck/comments/100jfl5/non_gr_rucking_events/">r/Goruck</a>) are great places to find information about local and regional events.</li>
    </ul>

    <h2>Key Takeaways</h2>
    <ul>
        <li><strong>Rucking competitions are endurance events that test physical and mental toughness by traversing distances with a weighted pack.</strong></li>
        <li><strong>They originate from military training and have evolved into a growing fitness trend with diverse event types.</strong></li>
        <li><strong>Participation offers numerous benefits, including enhanced fitness, mental resilience, community, and a sense of achievement.</strong></li>
        <li><strong>Training for a rucking competition requires progressive overload, strength training, and practice with competition weight.</strong></li>
        <li><strong>Resources like online directories and event organizers like GORUCK can help you find competitions near you.</strong></li>
    </ul>

    <h2>FAQ about Rucking Competitions</h2>

    <dl>
        <dt><strong>What weight should I carry in a rucking competition?</strong></dt>
        <dd>Weight requirements vary by event. Check the specific competition rules. Common weights range from 20-50 lbs, often with different requirements for men and women, or different weight classes.</dd>

        <dt><strong>What gear do I need for a rucking competition?</strong></dt>
        <dd>Essential gear includes a sturdy rucksack, weighted plates or sandbags, comfortable footwear, appropriate clothing for the weather, hydration (water bottles or bladder), and possibly nutrition. Check the event's gear list for specifics.</dd>

        <dt><strong>Are rucking competitions suitable for beginners?</strong></dt>
        <dd>Yes, there are rucking competitions for all fitness levels. Start with shorter distances and lighter weights, and gradually progress as you gain experience and fitness. Choose an event that aligns with your current fitness level.</dd>

        <dt><strong>How difficult are rucking competitions?</strong></dt>
        <dd>Rucking competitions are challenging, both physically and mentally. The difficulty depends on the distance, weight, terrain, and weather conditions. Proper training and preparation are key to successfully completing a competition.</dd>

        <dt><strong>Are there official rules for rucking competitions?</strong></dt>
        <dd>There are no universally standardized rules across all rucking competitions. Each event organizer sets its own rules regarding weight, course, time limits, and other specifics. Always review the rules of the specific competition you are entering.</dd>
    </dl>

    <h2>Conclusion</h2>
    <p>Rucking competitions offer a unique and rewarding way to challenge yourself, build resilience, and connect with a supportive community. Whether you're a seasoned rucker or new to the activity, exploring the competitive side of rucking can take your fitness journey to the next level. With careful preparation and a spirit of adventure, you can experience the satisfaction of conquering a rucking competition and discover what you're truly capable of. Lace up your boots, load your ruck, and find your next challenge!</p>

</body>
</html>
    """
    
    # Create an instance of WebMaster
    web_master = WebMaster()
    
    # Edit the post to fix HTML issues
    fixed_post = web_master.edit_post(sample_post)
    
    # Print the original and fixed posts for comparison
    print("\n=== ORIGINAL POST ===")
    print(sample_post)
    print("\n=== FIXED POST ===")
    print(fixed_post)


if __name__ == "__main__":
    main()
    
    