from django.apps import AppConfig

class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'

    def ready(self):
        # You can start background tasks here if needed
        pass

