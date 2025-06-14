import asyncio
import os
import csv
import time
import logging
import random
from datetime import datetime
import pytest
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from pathlib import Path
from conftest import CSV_PATH_2, SAMPLE_SIZE

load_dotenv("users.env")

REPORT_URL = 'https://app.powerbi.com/groups/me/reports/bd14751e-20b5-4c00-bb56-a171d311e151/ReportSection52325b70682a2cae3dad?ctid=d9f147f4-090d-4444-a562-1cac43890a3d&experience=power-bi'

def get_user_credentials(user_id):
    username_key = f"PBI_USERNAME_{user_id}"
    password_key = f"PBI_PASSWORD_{user_id}"
    return os.getenv(username_key), os.getenv(password_key)

CSV_FILENAME = "performance_log"
LOG_FILENAME = "performance_debug.log"

# TODO: Here the number of users can be adjusted
USER_IDS = list(range(6, 11))
NUM_USERS = len(USER_IDS)

# Discover test-file’s “base name” and build the output path
THIS_FILE = Path(__file__).resolve()
TEST_NAME = THIS_FILE.stem
OUTPUT_DIR = THIS_FILE.parent / TEST_NAME / f"number_of_users={NUM_USERS}"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Final CSV path
file_ts  = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
CSV_PATH = OUTPUT_DIR / f"performance_logs_{file_ts}.csv"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILENAME, mode='w'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
results = []

def random_wait(min_ms=60000, max_ms=120000):
    return random.randint(min_ms, max_ms)

@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", USER_IDS)  # Simulate n users
async def test_powerbi_load(user_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(ignore_https_errors=True, bypass_csp=True, 
                              record_har_path="perf.har",
                              locale='en-US', user_agent='PlaywrightTestAgent')
        
        
        page = await context.new_page()
        page.set_default_navigation_timeout(120000)
        page.set_default_timeout(120000)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        USERNAME, PASSWORD = get_user_credentials(user_id)

        if not USERNAME or not PASSWORD:
            logger.error(f"❌ [User {user_id}] Missing credentials in environment variables.")
            results.append([timestamp, user_id, "Missing credentials", "N/A"])
            return

        try:
            logger.info(f"[User {user_id}] Going to login URL...")
            await page.goto("https://app.powerbi.com/singleSignOn?experience=power-bi&ru=" + REPORT_URL)

            await page.get_by_role("textbox", name="Enter email").fill(USERNAME)
            await page.get_by_role("button", name="Submit").click()
            await page.get_by_role("textbox", name="Enter the password for").fill(PASSWORD)
            await page.get_by_role("button", name="Sign in").click()
            await page.get_by_role("button", name="Yes").click()

            # Clear Filters
            logger.info(f"[User {user_id}] Clearing any pre-applied filters...")
            try:
                await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()
                await page.wait_for_timeout(random_wait(8000, 12000))
                logger.info(f"[User {user_id}] 🧹 Filters cleared successfully.")
            except Exception as clear_err:
                logger.warning(f"[User {user_id}] ⚠️ 'Clear Filters' button not found or failed: {clear_err}")

            # Deselect any preselected dimensions
            logger.info(f"[User {user_id}] Deselecting any preselected dimensions...")
            try:
                selected_paths = page.locator('path.sub-selectable.selected')
                count = await selected_paths.count()
                if count > 0:
                    for i in range(count):
                        await selected_paths.nth(i).click()
                    logger.info(f"[User {user_id}] 🧹 Deselected {count} dimensions.")
                else:
                    logger.info(f"[User {user_id}] ✅ No preselected dimensions found.")
            except Exception as e:
                logger.warning(f"[User {user_id}] ⚠️ Failed to check/deselect dimensions: {e}")

            # Reset filters in the upper right corner
            await page.wait_for_selector("[data-testid='reset-to-default-btn']", timeout=5000)
            reset_btn = page.get_by_test_id("reset-to-default-btn")
            if await reset_btn.is_enabled():
                try:
                    await reset_btn.click()
                    await page.wait_for_selector("[data-testid='dailog-ok-btn']", timeout=5000)
                    await page.get_by_test_id("dailog-ok-btn").click()
                    logger.info(f"[User {user_id}] 🧹 Filters in the upper right corner have been reset successfully.")
                except Exception as modal_err:
                    logger.warning(f"[User {user_id}] ⚠️ Modal OK button failed: {modal_err}")
            else:
                logger.info(f"[User {user_id}] ℹ️ Reset button is disabled, nothing to do.")
                await page.wait_for_timeout(random_wait())
            
            await page.get_by_role("button", name="Κατάστημα").click()
            await page.wait_for_timeout(random_wait())
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            # Interactions - multiple insert filter
           
            await page.wait_for_timeout(5000)
            #container = page.locator("visual-container:nth-child(12)")
            #await container.hover()
            await page.wait_for_selector("visual-container:nth-child(12) visual-modern[data-testid=\"visual\"] div[data-testid=\"visual-content-desc\"] div.imageBackground" , timeout=20000)
            await page.locator("visual-container:nth-child(12) visual-modern[data-testid=\"visual\"] div[data-testid=\"visual-content-desc\"] div.imageBackground").click()
            # visual-container:nth-child(12) > transform > .visualContainer > .visualContent > .vcBody > .visualWrapper > .ng-star-inserted > .visual > .imageBackground
            #await page.wait_for_timeout(random_wait())

            with open(CSV_PATH_2, newline="") as f:
                reader = csv.reader(f)
                all_codes = [row[0].strip() for row in reader if row]
            selected = random.sample(all_codes, SAMPLE_SIZE)
            codes_text = "\n".join(selected)

            await page.wait_for_selector("iframe[name=\"visual-sandbox\"]", timeout=20000)

            await page.locator("iframe[name=\"visual-sandbox\"]").content_frame.get_by_role("textbox", name="Enter Item Codes").click()
            
            #import codes from csv
            await page.locator("iframe[name=\"visual-sandbox\"]").content_frame.get_by_role("textbox", name="Enter Item Codes").fill(codes_text)

            await page.get_by_test_id("focus-mode-btn").click()

            await page.wait_for_timeout(5000)
            
            # await page.locator("iframe[name=\"visual-sandbox\"]").content_frame.get_by_title("Include matches").click()
            await page.locator("iframe[name=\"visual-sandbox\"]").content_frame.get_by_title("Include matches").locator("i").nth(1).click()
            await page.get_by_test_id("back-to-report-button").click()
            await page.wait_for_timeout(5000)

            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            
            await page.wait_for_timeout(random_wait())

        

            # Date filter range
            target_start_date = "18/08/2024"
            slider = page.locator('div[role="slider"][aria-label="Date"]').first
            await slider.focus()
            max_attempts = 200
            attempts = 0
            while attempts < max_attempts:
                value = await slider.get_attribute("aria-valuetext")
                print(f"[Slider] Current: {value} | Target: {target_start_date}")
                if value == target_start_date:
                    break
                await slider.press("ArrowLeft")
                await page.wait_for_timeout(random_wait(80, 120))
                attempts += 1
            if attempts == max_attempts:
                print("⚠️ Reached maximum slider attempts. Target date not found.")
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()

            # Clear Filters
            await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()

            # Drill actions
            await page.get_by_label("S3 - Πωλήσεις Ειδών από 01/01").get_by_test_id("visual-title").get_by_text("S3 - Πωλήσεις Ειδών από 01/01").click()
            await page.get_by_test_id("drill-down-level-grouped-btn").click()
            await page.wait_for_timeout(random_wait())
            # Scroll down in the matrix after drill down
            try:
                matrix_locator = page.locator('div[role="region"][aria-label*="Matrix"]')
                await matrix_locator.wait_for(state="visible", timeout=10000)
                matrix_handle = await matrix_locator.element_handle()
                if matrix_handle:
                    await page.evaluate("el => el.scrollTop = el.scrollHeight", matrix_handle)
                    logger.info(f"[User {user_id}] 🖱️ Scrolled down in the matrix after drill down.")
                    await page.wait_for_timeout(random_wait())
                else:
                    logger.warning(f"[User {user_id}] ⚠️ Matrix element handle not found.")
            except Exception as scroll_err:
                logger.warning(f"[User {user_id}] ⚠️ Failed to scroll matrix: {scroll_err}")

            await page.get_by_label("S3 - Πωλήσεις Ειδών από 01/01").get_by_test_id("visual-title").get_by_text("S3 - Πωλήσεις Ειδών από 01/01").click()
            await page.get_by_test_id("drill-up-level-btn").click()
            await page.wait_for_timeout(random_wait())
            
            # Scroll up in the matrix after drill up
            try:
                matrix_locator = page.locator('div[role="region"][aria-label*="Matrix"]')
                await matrix_locator.wait_for(state="visible", timeout=10000)
                matrix_handle = await matrix_locator.element_handle()
                if matrix_handle:
                    await page.evaluate("el => el.scrollTop = 0", matrix_handle)
                    logger.info(f"[User {user_id}] 🖱️ Scrolled up in the matrix after drill up.")
                    await page.wait_for_timeout(random_wait(2000, 4000))
                else:
                    logger.warning(f"[User {user_id}] ⚠️ Matrix element handle not found for scroll up.")
            except Exception as scroll_err:
                logger.warning(f"[User {user_id}] ⚠️ Failed to scroll matrix up: {scroll_err}")

            # Clear Filters
            await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()
            await page.wait_for_timeout(random_wait())

            # Tab/Page switching
            await page.get_by_role("button", name="Σύγκριση Πωλήσεων").click()
            # Drill actions
            await page.get_by_label("S4 - Σύγκριση Πωλήσεις Ειδών").get_by_test_id("visual-title").get_by_text("S4 - Σύγκριση Πωλήσεις Ειδών").click()
            await page.get_by_test_id("drill-down-level-grouped-btn").click()
            await page.wait_for_timeout(random_wait())
            await page.get_by_label("S4 - Σύγκριση Πωλήσεις Ειδών").get_by_test_id("visual-title").get_by_text("S4 - Σύγκριση Πωλήσεις Ειδών").click()
            await page.get_by_test_id("drill-up-level-btn").click()
            await page.wait_for_timeout(random_wait())

            load_time_ms = round((time.time() - start_time) * 1000)
            logger.info(f"✅ [User {user_id}] Loaded in {load_time_ms} ms")

            with CSV_PATH.open("a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, user_id, "Success", load_time_ms])

        except Exception as e:
            logger.error(f"❌ [User {user_id}] Failed: {e}")
            with CSV_PATH.open("a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, user_id, f"Failed: {str(e)}", "N/A"])
        finally:
            await browser.close()

def teardown_module(module):
    logger.info(f"📄 Results saved to {CSV_PATH}")
    logger.info(f"📝 Debug log saved to {LOG_FILENAME}")
