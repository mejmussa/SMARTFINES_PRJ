import os
import django
import asyncio
import re
import requests
from django.utils import timezone
from datetime import datetime
from asgiref.sync import sync_to_async

# Only setup Django if running standalone
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartfines_prj.settings")
    django.setup()

# DB Functions (Wrapped with sync_to_async)
@sync_to_async
def mark_offenses_as_paid_if_missing(vehicle, current_modal_text):
    from monitoring.models import TrafficOffense
    known_unpaid = TrafficOffense.objects.filter(vehicle=vehicle, is_paid=False)
    references_on_page = set(re.findall(r'\b[A-Z0-9]{8,}\b', current_modal_text))

    for offense in known_unpaid:
        if offense.reference not in references_on_page:
            offense.is_paid = True
            offense.status = "PAID"
            offense.save()
            print(f"[✔] Marked as PAID: {offense.vehicle.plate_number} - {offense.reference}")

@sync_to_async
def save_offenses_to_db(text, vehicle):
    from monitoring.models import TrafficOffense
    from accounts.models import User

    print(f"\n[✓] Result for {vehicle.plate_number}\n" + "=" * 60)
    print("\n🔍 RAW MODAL TEXT START\n" + "-" * 60)
    print(text)
    print("-" * 60 + "\n🔍 RAW MODAL TEXT END\n")

    if "No pending offences found." in text:
        print("🟢 No pending offences found.")
        mark_offenses_as_paid_if_missing(vehicle, text)
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    headers_found = False
    seen_references = set()

    for line in lines:
        if not headers_found and line.startswith("SN"):
            headers_found = True
            continue

        elif headers_found and line[0].isdigit():
            try:
                match = re.search(
                    r"(.*?)\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s+(PENDING|PAID)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$",
                    line
                )
                if not match:
                    print("[!] Regex failed to parse line:", line)
                    continue

                prefix, charge, penalty, status, issued = match.groups()
                prefix_parts = prefix.strip().split(None, 4)
                if len(prefix_parts) < 5:
                    print("[!] Prefix split failed:", prefix_parts)
                    continue

                _, reference, license_no, location, offence = prefix_parts
                issued_date = timezone.make_aware(
                    datetime.strptime(issued.strip(), "%Y-%m-%d %H:%M:%S")
                )

                seen_references.add(reference)

                obj, created = TrafficOffense.objects.update_or_create(
                    vehicle=vehicle,
                    reference=reference,
                    defaults={
                        "user": vehicle.user,
                        "license": license_no,
                        "location": location,
                        "offence": offence,
                        "charge": float(charge),
                        "penalty": float(penalty),
                        "status": status,
                        "issued_date": issued_date,
                        "is_paid": (status == "PAID"),
                    }
                )

                if created:
                    print(f"[✔] Saved new offense: {reference}")
                else:
                    print(f"[↻] Updated offense: {reference}")

            except Exception as e:
                print(f"[x] Failed to process line: {e}")
                import traceback
                traceback.print_exc()

    mark_offenses_as_paid_if_missing(vehicle, text)
    print("=" * 60)

async def check_plate(plate):
    try:
        response = requests.post(
            "https://playwritepyprj-production.up.railway.app/api/automate",
            json={"url": "https://tms.tpf.go.tz/", "plate": plate},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("text", "No text returned")
        screenshot = data.get("screenshot")
        page_content = data.get("page_content", "")
        if "Modal error" in text:
            print(f"[!] Modal error for {plate}, page_content: {page_content}")
            if screenshot:
                import base64
                with open(f"screenshot_{plate}.png", "wb") as f:
                    f.write(base64.b16decode(screenshot))
        return text
    except requests.RequestException as e:
        print(f"[x] ❌ API request failed for {plate}: {str(e)}")
        return None

async def run_checker():
    from monitoring.models import Vehicle
    user_vehicles = await sync_to_async(lambda: list(Vehicle.objects.all()))()

    for vehicle in user_vehicles:
        try:
            modal_text = await check_plate(vehicle.plate_number)
            if modal_text:
                await save_offenses_to_db(modal_text, vehicle)
        except Exception as e:
            print(f"[x] Error checking {vehicle.plate_number}: {e}")

    print("\n[i] ✅ Check complete.\n")