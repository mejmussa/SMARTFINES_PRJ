FROM mcr.microsoft.com/playwright/python:v1.47.0-focal

WORKDIR /app

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Collect static files if you use them
RUN python manage.py collectstatic --noinput

# Gunicorn entry
CMD ["gunicorn", "smartfines_prj.wsgi:application", "--bind", "0.0.0.0:8000"]
