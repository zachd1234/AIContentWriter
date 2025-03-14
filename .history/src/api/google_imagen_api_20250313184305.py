import os
from dotenv import load_dotenv
from vertexai.preview.vision_models import ImageGenerationModel
import vertexai
import base64
import io
import requests
from PIL import Image

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
        Generate images using Google Imagen and return image bytes.
        
        Args:
            prompt (str): The prompt to generate images from
            number_of_images (int): Number of images to generate
            aspect_ratio (str): Aspect ratio of the images (e.g., "1:1", "16:9")
            
        Returns:
            list: List of tuples containing (image_bytes, filename)
        """
        try:
            # Generate images
            images = self.generation_model.generate_images(
                prompt=prompt,
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                add_watermark=True,
            )
            
            # Convert images to bytes
            image_data = []
            for i, image in enumerate(images):
                # Create a buffer to store the image
                img_byte_arr = io.BytesIO()
                
                # Save the PIL image to the buffer
                image._pil_image.save(img_byte_arr, format='JPEG')
                
                # Get the byte data
                img_byte_arr.seek(0)
                image_bytes = img_byte_arr.getvalue()
                
                # Create a filename
                filename = f"generated_image_{i+1}.jpg"
                
                # Add to results
                image_data.append((image_bytes, filename))
            
            return image_data
            
        except Exception as e:
            print(f"Error generating images: {str(e)}")
            return []

# Test the API if this file is run directly
if __name__ == "__main__":
    imagen_api = GoogleImagenAPI()
    
    # Test image generation
    prompt = "tired man rucking with a lot of weight on their back in the forest"
    image_data = imagen_api.generate_image(prompt)
    
    print(f"Generated {len(image_data)} images:")
    for image_bytes, filename in image_data:
        print(f"Image saved as: {filename}") 