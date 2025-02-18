import requests
from langchain.tools import Tool

# ✅ Replace this with your actual GetImg AI API key
API_KEY = "key-wHtXSzGfHsJsoJCCS8b1nu5FznStdiRjIq21CtzILjUr6nUl3a6Eryqxq8Q8Dgy12CQB8P8SC6m151riDyPePT8DyiFD1k5"
API_URL = "https://api.getimg.ai/v1/flux-schnell/text-to-image"  # Using Flux-Schnell model

def generate_image(prompt, width=1024, height=1024, steps=4, seed=None):
    """Generates an AI image based on the given prompt using GetImg AI."""

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
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Send API request
    response = requests.post(API_URL, json=data, headers=headers)

    # Print full API response for debugging
    print("🔹 Full API Response:", response.text)

    # Handle API response
    if response.status_code == 200:
        result = response.json()
        if "url" in result:  # ✅ Extract from `url`
            return result["url"]
        else:
            return "❌ No image URL returned in response."
    else:
        return f"❌ API Error: {response.status_code} - {response.text}"

# ✅ Convert generate_image() into a LangChain Tool
image_tool = Tool(
    name="AI Image Generator",
    func=generate_image,
    description="Generates an AI image based on a given prompt. Specify width, height, and steps if needed."
)

print(generate_image("a beautiful girl"))