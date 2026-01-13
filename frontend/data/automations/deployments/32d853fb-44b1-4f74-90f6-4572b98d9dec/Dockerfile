# Auto-generated Dockerfile for E2E Test Automation
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir websockets httpx aiofiles

# Copy the automation script
COPY automation.py /app/automation.py

# Create data directory
RUN mkdir -p /app/data

# Run the automation
CMD ["python", "-u", "automation.py"]
