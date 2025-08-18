FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates \
    libglib2.0-0 libnspr4 libnss3 libdbus-1-3 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcb1 libxkbcommon0 libatspi2.0-0 \
    libx11-6 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxrandr2 libgbm1 \
    libcairo2 libpango-1.0-0 libasound2 \
    gcc python3-dev libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps

COPY . .
CMD ["gunicorn", "trafficwatch_prj.wsgi:application", "--bind", "0.0.0.0:8000"]
