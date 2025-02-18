import requests
import base64
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import re
from openai import OpenAI

class WordPressMediaHandler:
    VISION_MODEL = "gpt-4o-mini"  # Correct model name
    VISION_ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def __init__(self, base_url: str, openai_api_key: str):
        print(f"Initializing WordPressMediaHandler with base_url: {base_url}")
        self.base_url = base_url.rstrip('/') + '/wp-json/wp/v2/'
        self.username = "zach"
        self.password = "anI6 BOd7 RDLL z4ET 7z0U fTrt"
        self.openai_api_key = "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"
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
    def set_auth_header(self):
        """Match the Java setAuthHeader method"""
        auth = f"{self.username}:{self.password}"
        encoded_auth = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
        return {
            'Authorization': f'Basic {encoded_auth}',
            'Accept': '*/*',  # Added to match Java's default headers
            'User-Agent': 'Python/requests'  # Added to match Java's default headers
        }

    def call_vision_model(self, image_url: str, prompt: str) -> str:
        try:
            request_body = {
                "model": self.VISION_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                                "detail": "auto"  # Let OpenAI decide resolution
                            }
                        }
                    ]
                }],
                "store": True,  # Added from documentation
                "max_tokens": 1000
            }

            print(f"Vision API Request: {json.dumps(request_body, indent=2)}")

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.VISION_ENDPOINT,
                headers=headers,
                json=request_body
            )

            print(f"Vision API Status Code: {response.status_code}")
            print(f"Vision API Response: {response.text}")

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

    def upload_image_from_url(self, image_url: str) -> str:
        try:
            print(f"Original image URL: {image_url}")
            
            # Generate metadata first
            metadata = self.generate_image_metadata(image_url)
            print(f"Generated metadata: {metadata}")
            
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content
            print(f"Downloaded image size: {len(image_data)} bytes")
            
            filename = f"{metadata['title']}-{int(time.time() * 1000)}.jpg"
            
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
            
            upload_url = f"{self.base_url}media"
            print(f"Uploading to: {upload_url}")
            
            response = requests.post(
                upload_url,
                headers=headers,
                data=multipart_data,
                verify=True
            )
            
            print(f"Response status: {response.status_code}")
            if response.status_code != 201:
                print(f"Error response: {response.text}")
                response.raise_for_status()
            
            media_response = response.json()
            # Only change: use guid.rendered instead of source_url
            wp_url = media_response['guid']['rendered']
            print(f"Upload successful. URL: {wp_url}")
            
            return wp_url
            
        except Exception as e:
            print(f"Error uploading media: {str(e)}")
            raise

def main():
    # Simplified test
    wp_handler = WordPressMediaHandler(base_url="https://ruckquest.com", openai_api_key="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")
    test_image_url = "https://koala.sh/api/image/v2-q0wvi-xbs3j.jpg?width=1216&#x26;height=832&#x26;dream"
    
    try:
        media_id = wp_handler.upload_image_from_url(
            image_url=test_image_url
        )
        print(f"Successfully uploaded image. WordPress URL: {media_id}")
    except Exception as e:
        print(f"Upload failed: {str(e)}")

if __name__ == "__main__":
    main() 