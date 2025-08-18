FROM python:3.11-slim

# Install Chrome
RUN apt-get update && apt-get install -y wget unzip libglib2.0-0 libnss3 libatk-bridge2.0-0 libdrm-dev libxrandr-dev libgbm-dev && \
    wget -q -O - https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb > /tmp/chrome.deb && \
    dpkg -i /tmp/chrome.deb || apt-get -y install -f && \
    rm /tmp/chrome.deb

# Set up app
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python", "monitoring/tms_check.py"]