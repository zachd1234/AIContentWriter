import requests
import os
from io import BytesIO
import base64

class WordPressMediaHandler:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/') + '/wp-json/wp/v2/media'
        message = 'zach:anI6 BOd7 RDLL z4ET 7z0U fTrt'
        base64_auth = base64.b64encode(message.encode()).decode()
        self.auth_header = f'Basic {base64_auth}'

    def upload_image_from_url(self, image_url: str) -> str:
        try:
            print(f"Downloading image from: {image_url}")
            response = requests.get(image_url)
            response.raise_for_status()
            
            filename = image_url.split('/')[-1].split('?')[0]  # Remove query parameters
            
            headers = {
                'Authorization': self.auth_header,
                'Accept': 'application/json',
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
            
            files = {
                'file': (filename, response.content, 'image/jpeg')
            }
            
            print(f"Uploading to: {self.base_url}")
            response = requests.post(
                self.base_url,
                headers=headers,
                files=files
            )
            
            print(f"Response status: {response.status_code}")
            if response.status_code != 201:
                print(f"Error response: {response.text}")
                response.raise_for_status()
            
            media_data = response.json()
            wp_url = media_data['source_url']
            print(f"Upload successful. URL: {wp_url}")
            
            return wp_url
            
        except Exception as e:
            print(f"Error uploading media: {str(e)}")
            raise

def main():
    # Simplified test
    wp_handler = WordPressMediaHandler(base_url="https://ruckquest.com")
    test_image_url = "https://koala.sh/api/image/v2-q0wvi-xbs3j.jpg?width=1216&#x26;height=832&#x26;dream"
    
    try:
        wp_url = wp_handler.upload_image_from_url(
            image_url=test_image_url
        )
        print(f"Successfully uploaded image. WordPress URL: {wp_url}")
    except Exception as e:
        print(f"Upload failed: {str(e)}")

if __name__ == "__main__":
    main() 