from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import re
import os
import django
import concurrent.futures
from django.utils import timezone
from monitoring.models import TrafficOffense

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trafficwatch_prj.settings")
django.setup()

# 1. SCANIA "T325EJR" , "T494EJR"  ZUBERI
# 2. SCANIA  "T869EMS", "T870EMS"  MUSSA MUSSA

PLATES = ["T291BWM", "T460DYA", "T797ARA", "T813BAW", "T859DJC", "T615BBE", "T847BJW", "T349DHU", "T869EMS", "T870EMS", "T152DHH", "T877DJY", "T325EJR", "T494EJR"] # 1. SCANIA "T325EJR", "T494EJR"
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


def mark_offenses_as_paid_if_missing(plate, current_modal_text):
    known_unpaid = TrafficOffense.objects.filter(plate_number=plate, is_paid=False)
    references_on_page = set(re.findall(r'\b[A-Z0-9]{8,}\b', current_modal_text))

    for offense in known_unpaid:
        if offense.reference not in references_on_page:
            offense.is_paid = True
            offense.status = "PAID"
            offense.save()
            print(f"[✔] Marked as PAID: {offense.plate_number} - {offense.reference}")


def save_offenses_to_db(text, plate):
    print(f"\n[✓] Result for {plate}\n" + "=" * 60)

    print("\n🔍 RAW MODAL TEXT START\n" + "-" * 60)
    print(text)
    print("-" * 60 + "\n🔍 RAW MODAL TEXT END\n")

    if "No pending offences found." in text:
        print("🟢 No pending offences found.")
        mark_offenses_as_paid_if_missing(plate, text)
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
                issued_date = timezone.make_aware(datetime.strptime(issued.strip(), "%Y-%m-%d %H:%M:%S"))

                seen_references.add(reference)

                try:
                    obj = TrafficOffense.objects.get(plate_number=plate, reference=reference)

                    updated = False
                    if (
                        obj.charge != float(charge) or
                        obj.penalty != float(penalty) or
                        obj.status != status or
                        obj.issued_date != issued_date or
                        obj.is_paid != (status == "PAID") or
                        obj.location != location or
                        obj.offence != offence
                    ):
                        obj.charge = float(charge)
                        obj.penalty = float(penalty)
                        obj.status = status
                        obj.issued_date = issued_date
                        obj.is_paid = (status == "PAID")
                        obj.location = location
                        obj.offence = offence
                        obj.save()
                        updated = True

                    if updated:
                        print(f"[↻] Updated offense: {reference}")
                    else:
                        print(f"[•] Offense exists, no changes: {reference}")

                except TrafficOffense.DoesNotExist:
                    TrafficOffense.objects.create(
                        user_id=1,
                        plate_number=plate,
                        reference=reference,
                        license=license_no,
                        location=location,
                        offence=offence,
                        charge=float(charge),
                        penalty=float(penalty),
                        status=status,
                        issued_date=issued_date,
                        is_paid=(status == "PAID"),
                    )
                    print(f"[✔] Saved new offense: {reference}")

            except Exception as e:
                print(f"[x] Failed to process line: {e}")
                import traceback
                traceback.print_exc()

    mark_offenses_as_paid_if_missing(plate, text)
    print("=" * 60)


def save_offenses_to_db_threadsafe(text, plate):
    return executor.submit(save_offenses_to_db, text, plate).result()


def check_plate(page, plate):
    page.goto("https://tms.tpf.go.tz/")
    page.wait_for_selector("input[placeholder*='Search by Registration']")

    print(f"\n[i] Typing plate: {plate}")
    page.fill("input[placeholder*='Search by Registration']", "")
    page.type("input[placeholder*='Search by Registration']", plate, delay=120)

    try:
        page.click("input[placeholder*='Search by Registration'] + button")
    except Exception as e:
        print(f"[!] Click failed, trying Enter instead: {e}")
        page.press("input[placeholder*='Search by Registration']", "Enter")

    print("[i] Waiting for modal to appear and load content...")
    try:
        page.wait_for_selector(".modal", timeout=10000)
        page.wait_for_function(
            """() => {
                const modal = document.querySelector('.modal');
                return modal && (modal.innerText || '').trim().length > 10;
            }""",
            timeout=10000,
        )
        print("[i] Modal is loaded.")
    except Exception as e:
        print(f"[x] ❌ Modal never appeared or had content for {plate}: {e}")
        return None

    try:
        modal_text = page.locator(".modal").inner_text()
        return str(modal_text)
    except Exception as e:
        print(f"[x] ❌ Failed to extract modal text: {e}")
        return None
    finally:
        try:
            page.click(".modal .close-btn")
        except:
            pass


def run_checker():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # False OR True FOR GUI USAGE 
        page = browser.new_page()

        while True:
            for i, plate in enumerate(PLATES):
                try:
                    modal_text = check_plate(page, plate)
                    if modal_text:
                        save_offenses_to_db_threadsafe(modal_text, plate)
                except Exception as e:
                    print(f"[x] Error checking {plate}: {e}")

                if i == len(PLATES) - 1:
                    try:
                        page.fill("input[placeholder*='Search by Registration']", "")
                    except:
                        print("[!] Failed to clear input.")

            print("\n[i] ✅ Round complete. Waiting 3600 seconds...\n")
            time.sleep(3600)  # 🔄 Adjust if needed (3600 for 1 hour)

        browser.close()


if __name__ == "__main__":
    run_checker()



