import os
from dotenv import load_dotenv
from vertexai.preview.vision_models import ImageGenerationModel
import vertexai
import base64
import requests
import tempfile
import uuid
from google.cloud import storage

class GoogleImagenAPI:
    def __init__(self):
        """Initialize the Google Imagen API client."""
        load_dotenv()
        
        # Get credentials from environment variables
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        
        # Load the image generation model
        self.generation_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
    
    def generate_image(self, prompt, number_of_images=1, aspect_ratio="1:1"):
        """
        Generate images using Google Imagen and return URLs.
        
        Args:
            prompt (str): The prompt to generate images from
            number_of_images (int): Number of images to generate
            aspect_ratio (str): Aspect ratio of the images (e.g., "1:1", "16:9")
            
        Returns:
            list: List of image URLs or paths
        """
        try:
            # Generate images
            images = self.generation_model.generate_images(
                prompt=prompt,
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                add_watermark=True,
            )
            
            # Save images to temporary files and return their paths
            image_urls = []
            for i, image in enumerate(images):
                # Create a unique filename
                filename = f"imagen_{uuid.uuid4()}.jpg"
                
                # Save the image to a temporary file
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                    image._pil_image.save(temp_file.name)
                    image_urls.append(temp_file.name)
            
            return image_urls
            
        except Exception as e:
            print(f"Error generating images: {str(e)}")
            return []

    def upload_to_cloud_storage(self, image_bytes, bucket_name):
        """Upload image to Google Cloud Storage and return public URL."""
        try:
            # Create a storage client
            storage_client = storage.Client()
            
            # Get the bucket
            bucket = storage_client.bucket(bucket_name)
            
            # Create a unique blob name
            blob_name = f"generated_images/{uuid.uuid4()}.jpg"
            blob = bucket.blob(blob_name)
            
            # Upload the image
            blob.upload_from_string(image_bytes, content_type="image/jpeg")
            
            # Make the blob publicly accessible
            blob.make_public()
            
            # Return the public URL
            return blob.public_url
        
        except Exception as e:
            print(f"Error uploading to Cloud Storage: {str(e)}")
            return None

# Test the API if this file is run directly
if __name__ == "__main__":
    imagen_api = GoogleImagenAPI()
    
    # Test image generation
    prompt = "tired man rucking with a lot of weight on their back in the forest"
    image_paths = imagen_api.generate_image(prompt)
    
    print(f"Generated {len(image_paths)} images:")
    for path in image_paths:
        print(f"Image saved at: {path}") 