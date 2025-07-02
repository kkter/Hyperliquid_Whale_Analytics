# Use a slim base image to keep size down
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/chromium
# Let webdriver-manager handle the driver path
# ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver # This line is no longer needed

# Install system dependencies needed by Chromium, then install Chromium itself.
# This is the key fix to prevent browser crashes.
# We also remove chromium-driver, as webdriver-manager will handle it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgtk-3-0 \
    libasound2 \
    libcups2 \
    libdbus-1-3 \
    libatk-bridge2.0-0 \
    libgbm1 \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Set up the application directory
WORKDIR /app
COPY . /app

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (if your app uses it, otherwise optional)
EXPOSE 5000

# The command to run your application will be specified in the `docker run` command
# or a docker-compose.yml file. For example: CMD ["python", "get_address.py"]
