import requests
from io import BytesIO
import base64
from requests_toolbelt.multipart.encoder import MultipartEncoder

class WordPressMediaHandler:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/') + '/wp-json/wp/v2/media'
        message = 'zach:anI6 BOd7 RDLL z4ET 7z0U fTrt'
        self.auth_header = f'Basic {base64.b64encode(message.encode()).decode()}'

    def upload_image_from_url(self, image_url: str) -> str:
        try:
            # Download image first
            print(f"Downloading image from: {image_url}")
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Prepare multipart form data
            filename = f"image-{hash(image_url)}.jpg"
            multipart_data = MultipartEncoder(
                fields={
                    'file': (filename, response.content, 'image/jpeg'),
                    'title': filename,
                    'alt_text': filename
                }
            )
            
            # Set headers
            headers = {
                'Authorization': self.auth_header,
                'Content-Type': multipart_data.content_type
            }
            
            print(f"Uploading to: {self.base_url}")
            response = requests.post(
                self.base_url,
                headers=headers,
                data=multipart_data
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