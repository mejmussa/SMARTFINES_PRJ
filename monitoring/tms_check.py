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

# --------------------
# Constants
# --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Always assume Linux (Railway/Heroku are Linux)
CHROME_BINARY_PATH = os.path.join(BASE_DIR, "bin/chromium/chrome")

# Use Chrome for Testing (headless shell) - lightweight and designed for servers
CHROME_HEADLESS_URL = "https://storage.googleapis.com/chrome-for-testing-public/139.0.7258.68/linux64/chrome-headless-shell-linux64.zip"

# Thread executor for DB writes
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


# --------------------
# Helper: Download & Extract Binary
# --------------------
def download_and_extract(url, target_dir):
    """
    Downloads and extracts a ZIP file to target_dir.
    Handles nested folders like chromedriver-linux64/chromedriver.
    """
    os.makedirs(target_dir, exist_ok=True)
    zip_path = os.path.join(target_dir, "tmp.zip")
    print(f"[↓] Downloading from {url}...")

    try:
        urllib.request.urlretrieve(url, zip_path)
        print(f"[✓] Downloaded to {zip_path}")
    except Exception as e:
        print(f"[❌] Failed to download: {e}")
        raise

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        os.remove(zip_path)
        print(f"[✓] Extracted to {target_dir}")
    except Exception as e:
        print(f"[❌] Failed to extract: {e}")
        raise

    # Handle nested folder (e.g., chrome-headless-shell-linux64/)
    extracted_items = os.listdir(target_dir)
    for item in extracted_items:
        path = os.path.join(target_dir, item)
        if os.path.isdir(path) and ("chrome" in item or "headless" in item):
            inner_chrome = os.path.join(path, "chrome-headless-shell")
            if not os.path.exists(inner_chrome):
                inner_chrome = os.path.join(path, "chrome")  # fallback

            if os.path.exists(inner_chrome):
                # Move to final location
                chromium_dir = os.path.dirname(CHROME_BINARY_PATH)
                os.makedirs(chromium_dir, exist_ok=True)
                os.rename(inner_chrome, CHROME_BINARY_PATH)
                os.rmdir(path)
                print(f"[✓] Moved chrome binary to {CHROME_BINARY_PATH}")
                return


# --------------------
# Ensure Chrome Binary is Available
# --------------------
def ensure_chrome_binary():
    """Downloads chrome-headless-shell if not already present."""
    if os.path.exists(CHROME_BINARY_PATH):
        print(f"[✓] Chrome binary already exists: {CHROME_BINARY_PATH}")
        return

    print("[⚙️] Chrome binary not found. Downloading chrome-headless-shell...")
    download_dir = os.path.join(BASE_DIR, "bin")
    download_and_extract(CHROME_HEADLESS_URL, download_dir)

    if not os.path.exists(CHROME_BINARY_PATH):
        raise RuntimeError("[❌] Failed to download or locate chrome-headless-shell after download.")

    # Make executable
    os.chmod(CHROME_BINARY_PATH, 0o755)
    print(f"[✓] Chrome binary is ready and executable: {CHROME_BINARY_PATH}")


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

    for line in lines:
        if not headers_found and line.startswith("SN"):
            headers_found = True
            continue

        if headers_found and line[0].isdigit():
            try:
                match = re.search(
                    r"(.*?)\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s+(PENDING|PAID)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$",
                    line
                )
                if not match:
                    print("[!] Regex failed to parse line:", line)
                    continue

                prefix, charge, penalty, status, issued = match.groups()
                parts = prefix.strip().split(None, 4)
                if len(parts) < 5:
                    print("[!] Prefix split failed:", parts)
                    continue

                _, reference, license_no, location, offence = parts
                issued_date = timezone.make_aware(datetime.strptime(issued.strip(), "%Y-%m-%d %H:%M:%S"))

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
                        "is_paid": status == "PAID",
                    }
                )

                action = "[✔] Saved new offense" if created else "[↻] Updated offense"
                print(f"{action}: {reference}")

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


# --------------------
# Main Runner
# --------------------
def run_checker():
    # Ensure Chrome binary is available
    try:
        ensure_chrome_binary()
    except Exception as e:
        print(f"[❌] Failed to setup Chrome: {e}")
        return

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")

    # Set binary location
    chrome_options.binary_location = CHROME_BINARY_PATH

    # Let Selenium Manager handle chromedriver automatically
    print("[🚀] Starting Chrome with Selenium Manager...")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[✓] WebDriver started successfully.")
    except Exception as e:
        print(f"[❌] Failed to start WebDriver: {e}")
        import traceback
        traceback.print_exc()
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
        try:
            driver.quit()
        except:
            pass
        executor.shutdown(wait=True)


# --------------------
# Entry Point
# --------------------
if __name__ == "__main__":
    run_checker()