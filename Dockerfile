FROM mcr.microsoft.com/playwright/python:v1.47.0-focal

WORKDIR /app

# Copy Python dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Run Gunicorn
CMD ["gunicorn", "smartfines_prj.wsgi:application", "--bind", "0.0.0.0:8000"]
