import requests
import base64
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import re
from openai import OpenAI

class WordPressMediaHandler:
    def __init__(self, base_url: str, openai_api_key: str):
        print(f"Initializing WordPressMediaHandler with base_url: {base_url}")
        self.base_url = base_url.rstrip('/') + '/wp-json/wp/v2/'
        self.username = "zach"
        self.password = "anI6 BOd7 RDLL z4ET 7z0U fTrt"
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

    def generate_image_metadata(self, image_url: str) -> dict:
        print("\n=== Generating Image Metadata ===")
        print(f"Using OpenAI to analyze image: {image_url}")
        try:
            prompt = """Analyze this image and provide SEO-optimized metadata for WordPress.

            Return ONLY a JSON object with these fields:
            - alt_text: Descriptive text for accessibility (under 125 chars)
            - title: Image title with words separated by dashes (under 60 chars)"""
            
            print("Sending request to OpenAI...")
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": image_url}
                        ]
                    }
                ],
                max_tokens=150
            )
            
            response_text = response.choices[0].message.content
            print(f"OpenAI Raw Response: {response_text}")
            
            # Clean up response
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```', '', response_text)
            print(f"Cleaned Response: {response_text}")
            
            metadata = json.loads(response_text.strip())
            print(f"Parsed Metadata: {metadata}")
            
            # Format title
            title = metadata.get('title', 'Image').lower()
            title = re.sub(r'[^a-z0-9\s-]', '', title)
            title = re.sub(r'\s+', '-', title)
            
            result = {
                'alt_text': metadata.get('alt_text', 'Image'),
                'title': title
            }
            print(f"Final Metadata: {result}")
            return result
            
        except Exception as e:
            print(f"ERROR in generate_image_metadata: {str(e)}")
            print(f"Error type: {type(e)}")
            if hasattr(e, 'response'):
                print(f"Response details: {e.response.text if hasattr(e.response, 'text') else 'No response text'}")
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