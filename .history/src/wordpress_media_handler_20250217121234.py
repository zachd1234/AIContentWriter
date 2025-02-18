import requests
import base64
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import re
from openai import OpenAI

class WordPressMediaHandler:
    VISION_MODEL = "gpt-4-mini"  # Match Java constant
    VISION_ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def __init__(self, base_url: str, openai_api_key: str):
        print(f"Initializing WordPressMediaHandler with base_url: {base_url}")
        self.base_url = base_url.rstrip('/') + '/wp-json/wp/v2/'
        self.username = "zach"
        self.password = "anI6 BOd7 RDLL z4ET 7z0U fTrt"
        self.openai_api_key = "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"
        self.openai_client = OpenAI(api_key="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")        
    def set_auth_header(self):
        """Match the Java setAuthHeader method"""
        auth = f"{self.username}:{self.password}"
        encoded_auth = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
        return {
            'Authorization': f'Basic {encoded_auth}',
            'Accept': '*/*',  # Added to match Java's default headers
            'User-Agent': 'Python/requests'  # Added to match Java's default headers
        }

    def call_vision_model(self, image_url: str, prompt: str, detail: str = None) -> str:
        """Match Java callVisionModel method exactly"""
        try:
            # Build request body to match Java exactly
            content = [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                        "detail": detail if detail else "auto"
                    }
                }
            ]

            request_body = {
                "model": self.VISION_MODEL,
                "messages": [{
                    "role": "user",
                    "content": content
                }],
                "max_tokens": 1000
            }

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.VISION_ENDPOINT,
                headers=headers,
                json=request_body
            )

            if not response.ok:
                error_body = response.text or "No error body"
                raise Exception(f"Vision API call failed: {error_body}")

            response_json = response.json()
            return response_json["choices"][0]["message"]["content"]

        except Exception as e:
            print(f"Error in vision analysis: {str(e)}")
            raise Exception("Failed to process vision request") from e

    def generate_image_metadata(self, image_url: str) -> dict:
        prompt = """Analyze this image and provide SEO-optimized metadata for WordPress.

        Return ONLY a JSON object with these fields:
        - alt_text: Descriptive text for accessibility (under 125 chars)
        - title: Image title with words separated by dashes (under 60 chars)"""

        try:
            response = self.call_vision_model(image_url, prompt)
            print(f"OpenAI Raw Response: {response}")
            
            # Clean up response
            response = response.replace("```json", "").replace("```", "").strip()
            metadata = json.loads(response)
            
            # Format title
            title = metadata.get('title', 'Image').lower()
            title = re.sub(r'[^a-z0-9\s-]', '', title)
            title = re.sub(r'\s+', '-', title)
            
            return {
                'alt_text': metadata.get('alt_text', 'Image'),
                'title': title
            }
            
        except Exception as e:
            print(f"Failed to generate metadata: {str(e)}")
            return {
                'alt_text': 'Image',
                'title': 'image'
            }

    def upload_image_from_url(self, image_url: str) -> int:
        print("\n=== Uploading Image ===")
        try:
            print(f"1. Original image URL: {image_url}")
            
            # Generate metadata
            metadata = self.generate_image_metadata(image_url)
            print(f"2. Generated metadata: {metadata}")
            
            # Download image
            print("3. Downloading image...")
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content
            print(f"4. Downloaded image size: {len(image_data)} bytes")
            
            # Prepare upload
            filename = f"{metadata['title']}-{int(time.time() * 1000)}.jpg"
            print(f"5. Generated filename: {filename}")
            
            multipart_data = MultipartEncoder(
                fields={
                    'file': (filename, image_data, 'image/jpeg'),
                    'alt_text': metadata['alt_text'],
                    'title': metadata['title']
                },
                boundary='----WebKitFormBoundary' + str(int(time.time() * 1000))
            )
            
            headers = {
                **self.set_auth_header(),
                'Content-Type': multipart_data.content_type,
                'Connection': 'keep-alive',
                'Accept': '*/*',
                'User-Agent': 'Python/requests'
            }
            print(f"6. Request headers: {headers}")
            
            upload_url = f"{self.base_url}media"
            print(f"7. Uploading to: {upload_url}")
            
            response = requests.post(
                upload_url,
                headers=headers,
                data=multipart_data,
                verify=True
            )
            
            print(f"8. Response status: {response.status_code}")
            print(f"9. Response headers: {dict(response.headers)}")
            print(f"10. Response content: {response.text[:200]}...")
            
            if response.status_code < 200 or response.status_code >= 300:
                raise Exception(f"API call failed with status {response.status_code}: {response.text}")
            
            media_response = response.json()
            media_id = media_response['id']
            print(f"11. Successfully uploaded. Media ID: {media_id}")
            
            return media_id
            
        except Exception as e:
            print(f"ERROR in upload_image_from_url: {str(e)}")
            print(f"Error type: {type(e)}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response.text if hasattr(e.response, 'text') else 'No response text'}")
            raise

def main():
    # Simplified test
    wp_handler = WordPressMediaHandler(base_url="https://ruckquest.com", openai_api_key="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")
    test_image_url = "https://koala.sh/api/image/v2-q0wvi-xbs3j.jpg?width=1216&#x26;height=832&#x26;dream"
    
    try:
        media_id = wp_handler.upload_image_from_url(
            image_url=test_image_url
        )
        print(f"Successfully uploaded image. WordPress ID: {media_id}")
    except Exception as e:
        print(f"Upload failed: {str(e)}")

if __name__ == "__main__":
    main() 