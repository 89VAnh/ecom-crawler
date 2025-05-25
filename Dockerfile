FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

# Set working directory
WORKDIR /home/pwuser/app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt