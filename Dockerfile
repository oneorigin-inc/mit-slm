FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for building Python packages
# Use single RUN command to reduce layers and ensure proper cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
# Remove build dependencies in the same layer to reduce image size
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge && \
    apt-get purge -y gcc && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app/ app/
COPY assets/ assets/

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Set Python to run in unbuffered mode for immediate log output
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

