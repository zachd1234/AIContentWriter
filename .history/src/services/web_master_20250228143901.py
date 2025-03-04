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
               - The exact problematic HTML snippet
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
                    print(f"  ❌ Issue #{i}: Could not find '{original_html[:30]}...' in the post")
            
            return fixed_post
            
        except Exception as e:
            print(f"\n❌ Error in edit_post: {str(e)}")
            return blog_post  # Return original post if there's an error

def main():
    """
    Demonstrates the WebMaster functionality with a sample blog post.
    """
    # Sample blog post with some HTML formatting issues
    sample_post = """<h2>Understanding Web Development Best Practices</h2>
    <p>Web development requires attention to detail and proper formatting.
    <p>Here are some common issues to watch for:
    <ul>
    <li>Unclosed tags can break your layout
    <li>Improper nesting creates rendering problems
    <li>Missing paragraph tags affect readability
    </ul>

    <p>When writing HTML, always remember to:
    <div>
    <p>Use proper indentation
    <p>Close all your tags properly
    <p>Validate your HTML regularly
    </div>

    <h3>Advanced Tips</h2>
    <p>For more complex websites, consider these advanced techniques:<p>
    <ol>
    <li>Use semantic HTML elements
    <li>Implement responsive design principles
    <li>Optimize for accessibility
    </ol>

    <a href=#>Learn more about web development</a>
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
    
    