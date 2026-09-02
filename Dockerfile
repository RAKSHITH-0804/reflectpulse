# Use a lightweight official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to optimize Python runtime container behavior
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Set the working directory in the container
WORKDIR /app

# Install system utilities needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to optimize docker build cache layers
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8080 for Google Cloud Run
EXPOSE 8080

# Configure healthcheck to ensure the container is responsive
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health || exit 1

# Execute Streamlit on container startup targeting Cloud Run specifications
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.enableCORS=false"]
