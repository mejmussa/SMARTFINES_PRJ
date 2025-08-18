from django.core.management.base import BaseCommand
import asyncio
from monitoring.tms_check import run_checker

class Command(BaseCommand):
    help = 'Run the vehicle plate checker'

    def handle(self, *args, **options):
        self.stdout.write("Starting vehicle plate checker...")
        asyncio.run(run_checker())
        self.stdout.write(self.style.SUCCESS("Checker completed successfully."))