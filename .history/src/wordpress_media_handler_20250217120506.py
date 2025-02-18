import requests
import base64
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json

class WordPressMediaHandler:
    def __init__(self, base_url: str):
        """Match the Java BaseWordPressClient constructor"""
        self.base_url = base_url.rstrip('/') + '/wp-json/wp/v2/'
        self.username = "zach"
        self.password = "anI6 BOd7 RDLL z4ET 7z0U fTrt"
        
    def set_auth_header(self):
        """Match the Java setAuthHeader method"""
        auth = f"{self.username}:{self.password}"
        encoded_auth = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
        return {
            'Authorization': f'Basic {encoded_auth}',
            'Accept': '*/*',  # Added to match Java's default headers
            'User-Agent': 'Python/requests'  # Added to match Java's default headers
        }

    def upload_image_from_url(self, image_url: str) -> int:
        """Match the Java uploadImage method exactly"""
        try:
            print(f"Original Unsplash URL: {image_url}")
            
            # Download image data first
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content
            print(f"Downloaded image size: {len(image_data)} bytes")
            
            # Create multipart form data
            filename = f"image-{int(time.time() * 1000)}.jpg"
            multipart_data = MultipartEncoder(
                fields={
                    'file': (filename, image_data, 'image/jpeg')
                },
                boundary='----WebKitFormBoundary' + str(int(time.time() * 1000))
            )
            
            # Set headers and make request
            headers = {
                **self.set_auth_header(),
                'Content-Type': multipart_data.content_type,
                'Connection': 'keep-alive'  # Added to match Java
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