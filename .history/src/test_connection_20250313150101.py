import requests
import time
import sys

def test_connection():
    """Test connection to the post-pitch service"""
    url = "https://post-pitch-fork.onrender.com/"
    
    print(f"Testing connection to {url}")
    
    try:
        # Test basic connectivity
        start_time = time.time()
        response = requests.get(url, timeout=10)
        elapsed_time = time.time() - start_time
        
        print(f"Response received in {elapsed_time:.2f} seconds")
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text[:200]}...")
        
        return True
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1) 