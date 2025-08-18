# monitoring/offense_announcer.py
import time
import pyttsx3
from django.db import models
from monitoring.models import TrafficOffense

PLATES = ["T291BWM", "T460DYA", "T797ARA"]

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 140)

    # Set female voice if available
    voices = engine.getProperty('voices')
    for voice in voices:
        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break

    engine.say(text)
    engine.runAndWait()
    engine.stop()

def announce_summary():
    offenses = TrafficOffense.objects.filter(
        plate_number__in=PLATES,
        is_paid=False,
    )
    total_unpaid = offenses.count()
    total_penalty = offenses.aggregate(total=models.Sum('penalty'))['total'] or 0

    if total_unpaid > 0:
        summary_text = (
            f"There are {total_unpaid} unpaid offense"
            + ("s" if total_unpaid > 1 else "")
            + f" for the monitored vehicles, with a total penalty amount of "
            f"{total_penalty:,.2f} Tanzanian shillings."
        )
        print("[Summary]:", summary_text)
        speak(summary_text)
    else:
        print("[i] No unpaid offenses found.")
        speak("There are no unpaid offenses for the monitored vehicles.")

def run_announcer_loop(poll_interval=60):
    print("[i] Starting offense summary announcer every 1 minute...\n")
    try:
        while True:
            announce_summary()
            print(f"[i] Waiting {poll_interval} seconds...\n")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n[i] Stopping announcer...")
