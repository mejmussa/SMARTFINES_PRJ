import os
import django
import asyncio
import re
import requests
from django.utils import timezone
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import deque

# Flag to control checker (set to True to always run, False to disable)
CHECKER_ENABLED = True

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

async def save_offenses_to_db(text, vehicle):
    from monitoring.models import TrafficOffense
    from accounts.models import User

    print(f"\n[✓] Result for {vehicle.plate_number}\n" + "=" * 60)
    print("\n🔍 RAW MODAL TEXT START\n" + "-" * 60)
    print(text)
    print("-" * 60 + "\n🔍 RAW MODAL TEXT END\n")

    if "No pending offences found." in text:
        print("🟢 No pending offences found.")
        await mark_offenses_as_paid_if_missing(vehicle, text)
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
                issued_date = await sync_to_async(timezone.make_aware)(
                    datetime.strptime(issued.strip(), "%Y-%m-%d %H:%M:%S")
                )

                seen_references.add(reference)

                obj, created = await sync_to_async(TrafficOffense.objects.update_or_create)(
                    vehicle=vehicle,
                    reference=reference,
                    defaults={
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

    await mark_offenses_as_paid_if_missing(vehicle, text)
    print("=" * 60)

async def check_plate(plate):
    # Set up retry strategy
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    try:
        response = session.post(
            "https://playwritepyprj-production.up.railway.app/api/automate",
            json={"url": "https://tms.tpf.go.tz/", "plate": plate},
            timeout=120,  # Increased timeout
            stream=True  # Enable streaming for large responses
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
    finally:
        session.close()

async def run_checker():
    from monitoring.models import Vehicle
    check_queue = deque()

    async def process_vehicle(vehicle):
        try:
            modal_text = await check_plate(vehicle.plate_number)
            if modal_text:
                await save_offenses_to_db(modal_text, vehicle)
            now = timezone.now()
            await sync_to_async(setattr)(vehicle, 'last_checked', now)
            await sync_to_async(vehicle.save)()
        except Exception as e:
            print(f"[x] Error checking {vehicle.plate_number}: {e}")

    while True:
        # Fetch vehicles and build queue of those due for checking
        user_vehicles = await sync_to_async(lambda: list(Vehicle.objects.all()))()
        now = timezone.now()
        check_queue.clear()  # Clear queue to avoid duplicates
        for vehicle in user_vehicles:
            if vehicle.last_checked is None or (now - vehicle.last_checked).total_seconds() >= vehicle.check_interval:
                check_queue.append(vehicle)

        # Log the queue
        print(f"[i] Queue size: {len(check_queue)} vehicles to check: {[v.plate_number for v in check_queue]}")

        # Process queue sequentially
        while check_queue:
            vehicle = check_queue.popleft()
            print(f"[i] Processing vehicle: {vehicle.plate_number}")
            await process_vehicle(vehicle)

        # If no vehicles, stop the loop
        if not user_vehicles:
            print("[i] No vehicles in database. Stopping checker.")
            break

        # Calculate sleep time until the next vehicle is due
        user_vehicles = await sync_to_async(lambda: list(Vehicle.objects.all()))()
        if not user_vehicles:
            print("[i] No vehicles in database after processing. Stopping checker.")
            break

        next_checks = [
            (vehicle.last_checked + timedelta(seconds=vehicle.check_interval) - now).total_seconds()
            for vehicle in user_vehicles if vehicle.last_checked is not None
        ]
        if not next_checks:
            print("[i] No vehicles with checks scheduled. Stopping checker.")
            break
        sleep_time = max(1, min(next_checks))  # Sleep until next due check, minimum 1 second
        print(f"[i] ✅ Queue processed. Waiting {sleep_time:.0f} seconds for next due vehicle...")
        await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    if CHECKER_ENABLED:
        print("[i] Checker enabled. Starting...")
        asyncio.run(run_checker())
    else:
        print("[i] Checker disabled. Exiting.")