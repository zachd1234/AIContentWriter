import requests
from langchain.tools import Tool

# ✅ Replace this with your actual GetImg AI API key
API_KEY = "key-wHtXSzGfHsJsoJCCS8b1nu5FznStdiRjIq21CtzILjUr6nUl3a6Eryqxq8Q8Dgy12CQB8P8SC6m151riDyPePT8DyiFD1k5"
API_URL = "https://api.getimg.ai/v1/flux-schnell/text-to-image"

def generate_image(prompt, width=1024, height=1024, steps=4, seed=None):
    """Generates an AI image based on the given prompt."""

    # Create request payload
    data = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "output_format": "jpeg",
        "response_format": "url"  # Ensures the API returns a direct image URL
    }

    # Add optional seed parameter
    if seed is not None:
        data["seed"] = seed

    # Set request headers
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Send API request
    response = requests.post(API_URL, json=data, headers=headers)

    # Print full API response for debugging
    print("🔹 Full API Response:", response.text)

    # Handle API response
    if response.status_code == 200:
        result = response.json()
        if "images" in result and len(result["images"]) > 0:
            return result["images"][0]["url"]  # Return first generated image URL
        else:
            return "❌ No images returned in the response."
    else:
        return f"❌ API Error: {response.status_code} - {response.text}"

# ✅ Test the function
if __name__ == "__main__":
    prompt = "Professional headshot of a business person, high quality, realistic, natural lighting"
    image_url = generate_image(prompt)
    print("Generated Image URL:", image_url)
