import requests
import os
from io import BytesIO
from PIL import Image
import json

class WordPressMediaHandler:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/') + '/wp-json/wp/v2/'
        self.auth = (username, password)

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
            
            # Upload to WordPress
            print("Uploading to WordPress...")
            upload_url = f"{self.base_url}media"
            headers = {
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
            
            response = requests.post(
                upload_url,
                auth=self.auth,
                files=files,
                data=data,
                headers=headers
            )
            response.raise_for_status()
            
            # Get media URL from response
            media_data = response.json()
            wp_url = media_data['source_url']
            print(f"Upload successful. URL: {wp_url}")
            
            return wp_url
            
        except Exception as e:
            print(f"Error uploading media: {str(e)}")
            raise

def main():
    # WordPress credentials
    wp_handler = WordPressMediaHandler(
        base_url="https://ruckquest.com",
        username="zach",
        password="XXXX-XXXX-XXXX-XXXX"  # Replace with your application password
    )
    
    # Test image URL
    test_image_url = "https://example.com/test-image.jpg"
    
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