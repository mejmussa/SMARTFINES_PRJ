# monitoring/apps.py
from django.apps import AppConfig
import subprocess

class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'

    def ready(self):
        # Install Chromium if missing
        try:
            subprocess.run(["which", "chromium-browser"], check=True)
        except subprocess.CalledProcessError:
            print("[i] Installing Chromium...")
            subprocess.run([
                "apt-get", "update"
            ], check=True)
            subprocess.run([
                "apt-get", "install", "-y", "chromium-browser"
            ], check=True)
