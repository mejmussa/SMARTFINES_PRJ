import time
import re
import os
import django
from datetime import datetime
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import platform
import urllib.request
import zipfile

# --------------------
# Django setup
# --------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartfines_prj.settings")
django.setup()

from monitoring.models import TrafficOffense
from .models import Vehicle
from django.utils import timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
system = platform.system()

# Thread executor for DB writes
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# --------------------
# Helper: Download & Extract with Cleanup
# --------------------
def download_and_extract(url, target_dir):
    """
    Downloads a ZIP file from URL and extracts it to target_dir.
    Handles nested folders (e.g., chromedriver-linux64/chromedriver).
    """
    os.makedirs(target_dir, exist_ok=True)
    zip_path = os.path.join(target_dir, "tmp.zip")
    print(f"[↓] Downloading from {url}...")
    urllib.request.urlretrieve(url, zip_path)
    print(f"[✓] Downloaded to {zip_path}")

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
    os.remove(zip_path)
    print(f"[✓] Extracted to {target_dir}")

    # Try to find the actual binary in nested folder
    extracted_folders = [f for f in os.listdir(target_dir) if os.path.isdir(os.path.join(target_dir, f))]
    for folder in extracted_folders:
        inner = os.path.join(target_dir, folder)
        if "chromedriver" in folder:
            src = os.path.join(inner, "chromedriver")
            dst = os.path.join(target_dir, "chromedriver")
            if os.path.exists(src) and not os.path.exists(dst):
                os.rename(src, dst)
            os.rmdir(inner)
        elif "chrome" in folder or "headless" in folder:
            src = os.path.join(inner, "chrome") if "chrome" in folder else os.path.join(inner, "chrome-headless-shell")
            dst = os.path.join(target_dir, "..", "chromium", "chrome")
            chromium_dir = os.path.dirname(dst)
            os.makedirs(chromium_dir, exist_ok=True)
            if os.path.exists(src) and not os.path.exists(dst):
                os.rename(src, dst)
            os.rmdir(inner)

# --------------------
# Download Chrome/Chromium for Linux if needed
# --------------------
if system == "Linux":
    # Use headless shell (lighter than full Chrome)
    CHROME_BINARY_PATH = os.path.join(BASE_DIR, "bin/chromium/chrome")
    CHROMEDRIVER_PATH = os.path.join(BASE_DIR, "bin/chromedriver")

    # URLs (✅ NO TRAILING SPACES!)
    CHROME_HEADLESS_URL = "https://storage.googleapis.com/chrome-for-testing-public/139.0.7258.68/linux64/chrome-headless-shell-linux64.zip"
    CHROMEDRIVER_URL = "https://storage.googleapis.com/chrome-for-testing-public/139.0.7258.68/linux64/chromedriver-linux64.zip"

    # Download headless shell
    if not os.path.exists(CHROME_BINARY_PATH):
        print("[⚙️] Chrome binary not found. Downloading headless shell...")
        download_and_extract(CHROME_HEADLESS_URL, os.path.join(BASE_DIR, "bin"))
        # Ensure it's executable
        if os.path.exists(CHROME_BINARY_PATH):
            os.chmod(CHROME_BINARY_PATH, 0o755)
            print(f"[✓] Chrome binary ready: {CHROME_BINARY_PATH}")

    # Optional: Manually download chromedriver (only if Selenium Manager fails)
    # But we'll let Selenium auto-manage it
    # Just ensure binary exists and is executable
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
# Main runner
# --------------------
def run_checker():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")

    # Set Chrome binary for Linux
    if system == "Linux":
        chrome_binary = os.path.join(BASE_DIR, "bin/chromium/chrome")
        if not os.path.exists(chrome_binary):
            print("[❌] Chrome binary missing! Cannot proceed.")
            return
        chrome_options.binary_location = chrome_binary
        print(f"[✓] Using Chrome binary: {chrome_binary}")

    # Let Selenium Manager handle chromedriver automatically (Selenium 4.6+)
    print("[🚀] Starting Chrome with Selenium Manager...")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[✓] WebDriver started successfully.")
    except Exception as e:
        print(f"[❌] Failed to start WebDriver: {e}")
        return

    try:
        while True:
            user_vehicles = Vehicle.objects.all()
            if not user_vehicles:
                print("[ℹ️] No vehicles to check. Waiting 3600s...")
                time.sleep(3600)
                continue

            for vehicle in user_vehicles:
                try:
                    modal_text = check_plate(driver, vehicle.plate_number)
                    if modal_text:
                        save_offenses_to_db_threadsafe(modal_text, vehicle)
                except Exception as e:
                    print(f"[x] Error checking {vehicle.plate_number}: {e}")
                    import traceback
                    traceback.print_exc()

            print("\n[i] ✅ Round complete. Waiting 3600 seconds...\n")
            time.sleep(3600)
    except KeyboardInterrupt:
        print("[🛑] Stopping checker...")
    finally:
        driver.quit()
        executor.shutdown(wait=True)


# --------------------
# Selenium Scraper
# --------------------
def check_plate(driver, plate):
    try:
        driver.get("https://tms.tpf.go.tz/")
    except Exception as e:
        print(f"[⚠️] Failed to load page: {e}")
        return None

    try:
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Search by Registration']"))
        )
        search_input.clear()
        search_input.send_keys(plate)

        # Try clicking search button or press Enter
        try:
            search_btn = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='Search by Registration'] + button")
            search_btn.click()
        except:
            search_input.send_keys(Keys.ENTER)

        # Wait for modal
        modal = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".modal"))
        )
        WebDriverWait(driver, 10).until(lambda d: len(modal.text.strip()) > 10)
        return modal.text

    except Exception as e:
        print(f"[x] ❌ Modal not found for {plate}: {e}")
        return None

    finally:
        # Try to close modal
        try:
            close_btn = driver.find_element(By.CSS_SELECTOR, ".modal .close-btn")
            close_btn.click()
            WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal")))
        except:
            pass  # Ignore if can't close
        
if __name__ == "__main__":
    run_checker()
