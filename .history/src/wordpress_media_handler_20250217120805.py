import requests
import base64
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import re
from openai import OpenAI

class WordPressMediaHandler:
    def __init__(self, base_url: str):
        """Match the Java BaseWordPressClient constructor"""
        self.base_url = base_url.rstrip('/') + '/wp-json/wp/v2/'
        self.username = "zach"
        self.password = "anI6 BOd7 RDLL z4ET 7z0U fTrt"
        self.openai_client = OpenAI(
            api_key="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")
        
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
        """Generate SEO-optimized metadata for the image using OpenAI's vision model"""
        try:
            prompt = """Analyze this image and provide SEO-optimized metadata for WordPress.

            Return ONLY a JSON object with these fields:
            - alt_text: Descriptive text for accessibility (under 125 chars)
            - title: Image title with words separated by dashes (under 60 chars)"""
            
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
            
            # Clean up the response
            response_text = response.choices[0].message.content
            print(f"DEBUG: Raw API response: {response_text}")
            
            # Remove markdown code blocks if present
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```', '', response_text)
            
            metadata = json.loads(response_text.strip())
            
            # Convert title to dash-separated format
            title = metadata.get('title', 'Image').lower()
            title = re.sub(r'[^a-z0-9\s-]', '', title)
            title = re.sub(r'\s+', '-', title)
            
            return {
                'alt_text': metadata.get('alt_text', 'Image'),
                'title': title
            }
            
        except Exception as e:
            print(f"Failed to parse JSON response: {str(e)}")
            return {
                'alt_text': 'Image',
                'title': 'image'
            }

    def upload_image_from_url(self, image_url: str) -> int:
        """Match the Java uploadImage method exactly"""
        try:
            print(f"Original Unsplash URL: {image_url}")
            
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
                verify=True  # Ensure SSL verification
            )
            
            response_body = response.text
            print(f"WordPress Media Response: {response_body}")
            
            if response.status_code < 200 or response.status_code >= 300:
                raise Exception(f"API call failed with status {response.status_code}: {response_body}")
            
            media_response = json.loads(response_body)
            media_id = media_response['id']
            print(f"Uploaded image ID: {media_id}")
            
            return media_id
            
        except Exception as e:
            print(f"Error uploading media: {str(e)}")
            raise

def main():
    # Simplified test
    wp_handler = WordPressMediaHandler(base_url="https://ruckquest.com")
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