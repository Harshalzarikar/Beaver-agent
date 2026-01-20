# Dockerfile
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Expose port for API
EXPOSE 8000

# Default command (Overridden in docker-compose)
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]