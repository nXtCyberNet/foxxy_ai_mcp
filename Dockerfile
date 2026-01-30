# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Create requirements.txt with detected dependencies

# Install Python dependencies
RUN pip install -r requirements.txt

# Expose port for FastAPI server (if running analytics_mcp_server.py)
EXPOSE 8000

# Default command - can be overridden
CMD ["python", "armoriq.py"]
