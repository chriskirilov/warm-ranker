# Use Python 3.12 slim image
FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Start the application
CMD ["python", "api_server.py"]
