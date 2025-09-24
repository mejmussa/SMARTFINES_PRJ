from django.apps import AppConfig
import asyncio
import threading
from monitoring.tms_check import run_checker
from django.db import OperationalError

class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'

    def ready(self):
        if not self.is_running_in_main_process():
            return

        def run_async_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_checker())
            finally:
                loop.close()

        try:
            from monitoring.models import CheckerConfig
            # Check if the checker is enabled in the database
            checker_config = CheckerConfig.objects.first()
            if checker_config and checker_config.is_enabled:
                thread = threading.Thread(target=run_async_in_thread, daemon=True)
                thread.start()
            else:
                print("[i] Checker is disabled in the database or no config exists.")
        except (OperationalError, ImportError):
            print("[i] Database not ready or CheckerConfig model not found. Skipping checker startup.")

    def is_running_in_main_process(self):
        import sys
        return not (sys.argv[0].endswith('manage.py') and sys.argv[1] in ['migrate', 'makemigrations'])