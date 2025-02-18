import requests

# ✅ Replace this with your actual GetImg AI API key
API_KEY = "key-wHtXSzGfHsJsoJCCS8b1nu5FznStdiRjIq21CtzILjUr6nUl3a6Eryqxq8Q8Dgy12CQB8P8SC6m151riDyPePT8DyiFD1k5"

# API Endpoint
url = "https://api.getimg.ai/v1/generate"

# Request Headers
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Request Payload
data = {
    "prompt": "Futuristic AI robot working on automation",
    "model": "stable-diffusion-xl",
    "num_images": 1  # Generate 1 image
}

# Send API Request
response = requests.post(url, json=data, headers=headers)

# Print Response
if response.status_code == 200:
    result = response.json()
    print("✅ GetImg AI Connection Successful!")
    print("Generated Image URL:", result["images"][0]["url"])
else:
    print("❌ Error:", response.status_code, response.text)
