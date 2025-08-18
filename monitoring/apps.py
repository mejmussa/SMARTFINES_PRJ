from django.apps import AppConfig
import asyncio
import threading
from monitoring.tms_check import run_checker

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

        thread = threading.Thread(target=run_async_in_thread, daemon=True)
        thread.start()

    def is_running_in_main_process(self):
        import sys
        return not (sys.argv[0].endswith('manage.py') and sys.argv[1] in ['migrate', 'makemigrations'])