import os
import django
import time
import subprocess
from datetime import datetime
from collections import defaultdict

# === Setup Django environment ===
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trafficwatch_prj.settings')  # ✅ your Django project
django.setup()

from monitoring.models import TrafficOffense  # ✅ replace with actual app name


# === Lightweight Offense class ===
class Offense:
    def __init__(self, plate, ref, lic, loc, desc, charge, penalty, status, date):
        self.plate = plate
        self.ref = ref
        self.lic = lic
        self.loc = loc
        self.desc = desc
        self.charge = charge
        self.penalty = penalty
        self.status = status
        self.date = date


# === Detect connected ADB device ===
def get_adb_serial_number():
    try:
        result = subprocess.run(['adb', 'devices'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in result.stdout.splitlines()[1:]:
            if line.strip() and "device" in line:
                serial = line.split()[0]
                print(f"[✅] ADB Device: {serial}")
                return serial
        print("[⚠️] No ADB device connected.")
    except Exception as e:
        print(f"[❌] ADB error: {e}")
    return None


# === Helpers ===
def truncate(text, limit):
    return text[:limit] + '...' if len(text) > limit else text


def create_offense_sms(o):
    total = int(o.charge + o.penalty)
    return (
        f"{o.plate} at {truncate(o.loc, 12)}: "
        f"{truncate(o.desc, 25)} Ref:{o.ref} "
        f"Charge:{int(o.charge)} Penalty:{int(o.penalty)} Total:{total} "
        f"Date:{o.date.strftime('%m/%d %H:%M')}"
    )


def create_summary_sms(plate, offenses):
    total_c = sum(o.charge for o in offenses)
    total_p = sum(o.penalty for o in offenses)
    total = total_c + total_p
    return f"{plate}: {len(offenses)} offenses. Charge:{int(total_c)} Penalty:{int(total_p)} Total:{int(total)}"


def send_sms_via_adb(serial, phone, body):
    if not phone.startswith('+'):
        phone = '+' + phone

    cmd = (
        f'adb -s {serial} shell "input keyevent KEYCODE_WAKEUP; '
        f'am start -a android.intent.action.SENDTO -d sms:{phone} '
        f'--es sms_body \\"{body}\\"; sleep 1.5; '
        f'input keyevent 22; input keyevent 22; input keyevent 66"'
    )
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        print(f"[✅] Sent to {phone}: {body}")
    else:
        print(f"[❌] ADB Error: {result.stderr.decode()}")


# === Main Loop ===
def run_sms_sender_loop():
    phone_numbers = ["255717455602", "255712151635"]  # ✅ Replace or extend , "255767484562","255763140282", 
    serial = get_adb_serial_number()
    if not serial:
        return

    print("[🔁] Starting SMS sender loop...")

    while True:
        offenses_qs = TrafficOffense.objects.filter(status='PENDING', is_paid=False).order_by('plate_number', 'issued_date')

        if not offenses_qs.exists():
            print("[⏳] No offenses found. Rechecking in 10 seconds...")
            time.sleep(10)
            continue  # Check again after 10 seconds

        # Group by plate number
        plate_offenses = defaultdict(list)
        for o in offenses_qs:
            offense = Offense(
                plate=o.plate_number,
                ref=o.reference,
                lic=o.license,
                loc=o.location,
                desc=o.offence,
                charge=float(o.charge),
                penalty=float(o.penalty),
                status=o.status,
                date=o.issued_date
            )
            plate_offenses[o.plate_number].append(offense)

        # Send SMS to each phone number
        for phone in phone_numbers:
            for plate, offenses in plate_offenses.items():
                for o in offenses:
                    sms = create_offense_sms(o)
                    send_sms_via_adb(serial, phone, sms)
                    time.sleep(2)

                # Send summary
                summary = create_summary_sms(plate, offenses)
                time.sleep(5)
                send_sms_via_adb(serial, phone, summary)

        print("[⏸️] Done sending all messages. Sleeping for 3 hours...")
        time.sleep(3 * 60 * 60)


# === Entry point ===
if __name__ == "__main__":
    run_sms_sender_loop()
