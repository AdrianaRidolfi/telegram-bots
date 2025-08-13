# Use Python 3.11 slim for smaller image size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for your packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better Docker layer caching
COPY quiz_bot/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the entire quiz_bot directory
COPY quiz_bot/ .

# Create directories for runtime files
RUN mkdir -p /app/temp /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# FIXED: Use PORT environment variable that Koyeb provides
# Default to 8080 but allow override via environment
ENV PORT=8080
EXPOSE $PORT

# Add healthcheck for better monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Run the bot
CMD ["python", "bot.py"]