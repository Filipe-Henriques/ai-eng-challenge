# Use Python 3.11 slim base image for optimal size (~120MB)
FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file and install Python dependencies
# (Separate layer for better caching - dependencies change less frequently than code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy application source code
COPY . .

# Copy and set permissions for startup script (force LF line endings)
COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

# Set file ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Start application using startup script
CMD ["/app/start.sh"]
