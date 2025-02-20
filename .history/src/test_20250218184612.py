import google.generativeai as genai

# Configure
genai.configure(api_key="AIzaSyAgBew-UTCDpKGAb1qidbs0CrfC9nKU9ME")

# Print version and available models
print(f"Version: {genai.__version__}")
print("\nAvailable Models:")
for m in genai.list_models():
    print(m.name)

# Create model
model = genai.GenerativeModel('gemini-pro')

# Print model configuration options
print("\nModel Configuration Options:")
print(model.generate_content.__doc__)