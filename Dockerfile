FROM mcr.microsoft.com/playwright/python:v1.47.0-focal

# Install only needed build deps
RUN apt-get update && apt-get install -y \
    gcc python3-dev libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Browsers already installed in this image, no need for --with-deps
RUN playwright install

COPY . .

CMD ["gunicorn", "smartfines_prj.wsgi:application", "--bind", "0.0.0.0:8000"]
