import requests
import os
from io import BytesIO
from PIL import Image
import json

class WordPressMediaHandler:
    def __init__(self):
        # Hardcoded credentials
        self.base_url = "https://ruckquest.com/wp-json/wp/v2/"
        self.auth = ("zach", "anI6 BOd7 RDLL z4ET 7z0U fTrt")  # You'll replace this

    def upload_image_from_url(self, image_url: str, title: str = None) -> str:
        """
        Downloads an image from URL and uploads it to WordPress
        
        Args:
            image_url (str): URL of the image to download
            title (str): Optional title for the media
            
        Returns:
            str: WordPress media URL
        """
        try:
            # Download image
            print(f"Downloading image from: {image_url}")
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Create file-like object from image data
            img_data = BytesIO(response.content)
            
            # Get image metadata
            with Image.open(img_data) as img:
                filename = f"image_{hash(image_url)}.{img.format.lower()}"
            
            # Prepare upload
            files = {
                'file': (filename, img_data.getvalue(), 'image/jpeg')
            }
            
            data = {}
            if title:
                data['title'] = title
            
            # Upload to WordPress with updated headers
            print("Uploading to WordPress...")
            upload_url = f"{self.base_url}media"
            headers = {
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Accept': 'application/json',
                'Content-Type': 'multipart/form-data'
            }
            
            response = requests.post(
                upload_url,
                auth=self.auth,
                files=files,
                data=data,
                headers=headers,
                verify=True  # Added SSL verification
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response.text}")
            
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
    wp_handler = WordPressMediaHandler()
    test_image_url = "https://koala.sh/api/image/v2-q0wvi-xbs3j.jpg?width=1216&#x26;height=832&#x26;dream"
    
    try:
        wp_url = wp_handler.upload_image_from_url(
            image_url=test_image_url,
            title="Test Upload"
        )
        print(f"Successfully uploaded image. WordPress URL: {wp_url}")
    except Exception as e:
        print(f"Upload failed: {str(e)}")

if __name__ == "__main__":
    main() 