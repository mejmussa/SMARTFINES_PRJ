from django.apps import AppConfig
import subprocess


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'

    def ready(self):
        try:
            subprocess.run(['playwright', 'install'], check=True)
        except Exception as e:
            print("Playwright install failed:", e)
