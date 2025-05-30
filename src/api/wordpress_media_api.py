import requests
import base64
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import re
import google.generativeai as genai
import PIL.Image
import io
import os
from dotenv import load_dotenv

class WordPressMediaHandler:
    VISION_MODEL = "gemini-2.0-flash"  # Updated to the new model name

    def __init__(self, base_url: str):
        # Load environment variables
        load_dotenv()
        
        print(f"Initializing WordPressMediaHandler with base_url: {base_url}")
        # Ensure base_url is properly formatted and includes wp-json endpoint
        self.base_url = base_url.rstrip('/') + '/wp-json/wp/v2/'
        
        # Get credentials from environment variables
        self.username = os.getenv('WP_USERNAME')
        self.password = os.getenv('WP_PASSWORD')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        
        if not all([self.username, self.password, self.google_api_key]):
            raise ValueError("Missing required environment variables")
        
        # Configure Gemini
        genai.configure(api_key=self.google_api_key)
        self.model = genai.GenerativeModel(self.VISION_MODEL)
        
    def set_auth_header(self):
        """Match the Java setAuthHeader method"""
        auth = f"{self.username}:{self.password}"
        encoded_auth = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
        return {
            'Authorization': f'Basic {encoded_auth}',
            'Accept': '*/*',
            'User-Agent': 'Python/requests'
        }

    def call_vision_model(self, image_url: str, prompt: str) -> str:
        try:
            print(f"Downloading image from: {image_url}")
            # Download the image
            response = requests.get(image_url)
            response.raise_for_status()
            print(f"Image downloaded successfully, size: {len(response.content)} bytes")
            
            try:
                # Convert image bytes to PIL Image
                image = PIL.Image.open(io.BytesIO(response.content))
                
                # Generate content using Gemini
                print("Calling Gemini Vision API...")
                response = self.model.generate_content([
                    prompt,
                    image  # Pass PIL Image object
                ])
                
                print(f"Raw Gemini Response: {response}")
                
                if not response:
                    raise Exception("Empty response from Gemini Vision API")
                
                return response.text

            except Exception as gemini_error:
                print(f"Gemini API Error: {str(gemini_error)}")
                print(f"Error type: {type(gemini_error)}")
                raise

        except requests.exceptions.RequestException as download_error:
            print(f"Image download error: {str(download_error)}")
            raise Exception("Failed to download image") from download_error
        except Exception as e:
            print(f"Unexpected error in vision analysis: {str(e)}")
            print(f"Error type: {type(e)}")
            raise Exception("Failed to process vision request") from e

    def generate_image_metadata(self, image_url: str) -> dict:
        prompt = """Analyze this image and provide SEO-optimized metadata for WordPress.

        Return ONLY a JSON object with these fields:
        - alt_text: Descriptive text for accessibility (under 125 chars)
        - title: Image title with words separated by dashes (under 60 chars)"""

        try:
            response = self.call_vision_model(image_url, prompt)
            
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
            wp_url = media_response['guid']['rendered']
            print(f"Upload successful. URL: {wp_url}")
            
            return wp_url
            
        except Exception as e:
            print(f"Error uploading media: {str(e)}")
            raise

    def upload_image_bytes(self, image_bytes, filename):
        """
        Upload image bytes to WordPress.
        
        Args:
            image_bytes (bytes): The image data as bytes
            filename (str): The filename to use
            
        Returns:
            str: URL of the uploaded image
        """
        try:
            print(f"Uploading image bytes with filename: {filename}")
            
            # Convert bytes to PIL Image for Gemini Vision analysis
            image = PIL.Image.open(io.BytesIO(image_bytes))
            
            # Generate metadata using Gemini Vision
            prompt = """Analyze this image and provide SEO-optimized metadata for WordPress.

            Return ONLY a JSON object with these fields:
            - alt_text: Descriptive text for accessibility (under 125 chars)
            - title: Image title with words separated by dashes (under 60 chars)"""
            
            try:
                response = self.model.generate_content([
                    prompt,
                    image  # Pass PIL Image object
                ])
                
                # Clean up response
                response_text = response.text
                response_text = response_text.replace("```json", "").replace("```", "").strip()
                metadata = json.loads(response_text)
                
                # Format title
                title = metadata.get('title', 'Image').lower()
                title = re.sub(r'[^a-z0-9\s-]', '', title)
                title = re.sub(r'\s+', '-', title)
                
                metadata = {
                    'alt_text': metadata.get('alt_text', 'Image'),
                    'title': title
                }
                
            except Exception as e:
                print(f"Failed to generate metadata: {str(e)}")
                # Fallback metadata
                title = filename.replace('.jpg', '').replace('-', ' ')
                title = re.sub(r'generated_image_\d+_\d+', '', title).strip()
                if not title:
                    title = "AI generated image"
                
                title = title.lower()
                title = re.sub(r'[^a-z0-9\s-]', '', title)
                title = re.sub(r'\s+', '-', title)
                
                metadata = {
                    'alt_text': f"AI generated image: {title.replace('-', ' ')}",
                    'title': title
                }
            
            print(f"Generated metadata: {metadata}")
            
            # Create filename with metadata title
            filename = f"{metadata['title']}-{int(time.time() * 1000)}.jpg"
            
            multipart_data = MultipartEncoder(
                fields={
                    'file': (filename, image_bytes, 'image/jpeg'),
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
            wp_url = media_response['guid']['rendered']
            print(f"Upload successful. URL: {wp_url}")
            
            return wp_url
            
        except Exception as e:
            print(f"Error uploading image bytes: {str(e)}")
            return ""

def main():
    # Updated test function with dynamic base URL
    base_url = "https://example.com"  # Replace with your test domain
    wp_handler = WordPressMediaHandler(base_url=base_url)
    
    test_image_url = "https://example.com/test-image.jpg"  # Replace with a real test image
    
    print("test starting")
    try:
        media_url = wp_handler.upload_image_from_url(image_url=test_image_url)
        print(f"Successfully uploaded image. WordPress URL: {media_url}")
    except Exception as e:
        print(f"Upload failed: {str(e)}")

if __name__ == "__main__":
    main() 