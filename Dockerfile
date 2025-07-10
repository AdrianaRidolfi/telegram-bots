# Use Python 3.11 slim image
FROM python:3.11

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY quiz_bot/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy firebase credentials first
COPY firebase-credentials.json .

# Copy the entire quiz_bot directory
COPY quiz_bot/ .

# Create directory for any runtime files
RUN mkdir -p /app/temp

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port (optional, depends on your bot)
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]