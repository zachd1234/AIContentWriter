import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

# Load environment variables
load_dotenv()

def test_vertex_connection():
    try:
        # Initialize Vertex AI
        vertexai.init(project="your-project-id", location="us-central1")
        
        # Create model
        model = GenerativeModel("gemini-1.5-pro")
        
        # Test simple generation
        response = model.generate_content(
            "What is 2+2? Please answer with just the number.",
            generation_config={"temperature": 0},
        )
        
        print("Connection successful!")
        print(f"Test response: {response.text}")
        
    except Exception as e:
        print(f"Error connecting to Vertex AI: {str(e)}")

if __name__ == "__main__":
    test_vertex_connection() 