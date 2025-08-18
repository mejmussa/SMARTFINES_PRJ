import time
import re
import os
import django
from datetime import datetime
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartfines_prj.settings")
django.setup()

from monitoring.models import TrafficOffense
from accounts.models import User
from .models import Vehicle
from django.utils import timezone

# Thread executor for DB writes
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# --------------------
# DB Functions
# --------------------
def mark_offenses_as_paid_if_missing(vehicle, current_modal_text):
    known_unpaid = TrafficOffense.objects.filter(vehicle=vehicle, is_paid=False)
    references_on_page = set(re.findall(r'\b[A-Z0-9]{8,}\b', current_modal_text))

    for offense in known_unpaid:
        if offense.reference not in references_on_page:
            offense.is_paid = True
            offense.status = "PAID"
            offense.save()
            print(f"[✔] Marked as PAID: {offense.vehicle.plate_number} - {offense.reference}")


def save_offenses_to_db(text, vehicle):
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
                issued_date = timezone.make_aware(datetime.strptime(issued.strip(), "%Y-%m-%d %H:%M:%S"))

                seen_references.add(reference)

                # Update or create offense
                obj, created = TrafficOffense.objects.update_or_create(
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

    mark_offenses_as_paid_if_missing(vehicle, text)
    print("=" * 60)


def save_offenses_to_db_threadsafe(text, vehicle):
    return executor.submit(save_offenses_to_db, text, vehicle).result()


# --------------------
# Selenium Scraper
# --------------------
def check_plate(driver, plate):
    driver.get("https://tms.tpf.go.tz/")
    
    search_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Search by Registration']")
    search_input.clear()
    search_input.send_keys(plate)

    # Try clicking search button, fallback to Enter
    try:
        search_btn = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Search by Registration'] + button")
        search_btn.click()
    except:
        search_input.send_keys(Keys.ENTER)

    try:
        modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".modal"))
        )
        WebDriverWait(driver, 10).until(lambda d: len(modal.text.strip()) > 10)
        return modal.text

    except Exception as e:
        print(f"[x] ❌ Modal not found for {plate}: {e}")
        return None

    finally:
        try:
            close_btn = driver.find_element(By.CSS_SELECTOR, ".modal .close-btn")
            close_btn.click()
        except:
            pass


def run_checker():
    chrome_options = Options()
    #chrome_options.headless = True
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # System ChromeDriver path
    driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=chrome_options)

    try:
        while True:
            # Fetch all vehicles in DB
            user_vehicles = Vehicle.objects.all()

            for vehicle in user_vehicles:
                try:
                    modal_text = check_plate(driver, vehicle.plate_number)
                    if modal_text:
                        save_offenses_to_db_threadsafe(modal_text, vehicle)
                except Exception as e:
                    print(f"[x] Error checking {vehicle.plate_number}: {e}")

            print("\n[i] ✅ Round complete. Waiting 3600 seconds...\n")
            time.sleep(3600)

    finally:
        driver.quit()


if __name__ == "__main__":
    run_checker()
