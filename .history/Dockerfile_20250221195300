# Use Python slim image to keep size down
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy all files (maintaining directory structure)
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Python path
ENV PYTHONPATH=/app

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3000"]