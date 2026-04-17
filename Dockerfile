# Use a slim Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed (none currently required for this project)
# RUN apt-get update && apt-get install -y ...

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# .dockerignore will handle excluding .env and other secrets
COPY . .

# Expose the port Hugging Face Spaces expects
EXPOSE 7860

# Define environment variables (defaults, will be overridden by HF Secrets)
ENV PORT=7860

# Command to run the application
CMD ["python", "app.py"]
