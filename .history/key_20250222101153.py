import secrets

api_key = secrets.token_hex(16)  # Generates a random 32-character hex string
print(api_key)