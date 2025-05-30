import asyncio
import os
import csv
import time
import logging
from datetime import datetime
import pytest
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from pathlib import Path

load_dotenv("users.env")
REPORT_URL = 'https://app.powerbi.com/groups/me/reports/79598554-679c-48e4-971f-b0862b2ff756/ReportSection52325b70682a2cae3dad?ctid=d9f147f4-090d-4444-a562-1cac43890a3d&experience=power-bi'

def get_user_credentials(user_id):
    username_key = f"PBI_USERNAME_{user_id}"
    password_key = f"PBI_PASSWORD_{user_id}"
    return os.getenv(username_key), os.getenv(password_key)

CSV_FILENAME = "performance_log"
LOG_FILENAME = "performance_debug.log"

# TODO: Here the number of users can be adjusted
USER_IDS = list(range(1, 71))
NUM_USERS = len(USER_IDS)

# Discover test-file’s “base name” and build the output path
THIS_FILE = Path(__file__).resolve()
TEST_NAME = THIS_FILE.stem                           
OUTPUT_DIR = THIS_FILE.parent                         \
            / TEST_NAME                                \
            / f"number_of_users={NUM_USERS}"          
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
                await page.wait_for_timeout(10000)
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
                    # click the reset button
                    await reset_btn.click()
                    # wait up to 5s for the modal’s OK button to appear
                    await page.wait_for_selector("[data-testid='dailog-ok-btn']", timeout=5000)
                    # click the OK button
                    await page.get_by_test_id("dailog-ok-btn").click()
                    logger.info(f"[User {user_id}] 🧹 Filters in the upper right corner have been reset successfully.")
                except Exception as modal_err:
                    logger.warning(f"[User {user_id}] ⚠️ Modal OK button failed: {modal_err}")
            else:
                logger.info(f"[User {user_id}] ℹ️ Reset button is disabled, nothing to do.")

            # Interactions
            await page.get_by_role("button", name="Κατάστημα").click()
            await page.wait_for_timeout(10000)
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            await page.get_by_role("rowheader", name="Collapsed 101 - ΚΡΥΣΤΑΛΛΗ").get_by_label("Collapsed").click()
            await page.wait_for_timeout(10000)
            #await page.get_by_role("rowheader", name="Collapsed 101 - ΚΡΥΣΤΑΛΛΗ").wait_for(state="visible", timeout=5000)
            await page.get_by_role("button", name="Expanded").click()
            await page.wait_for_timeout(60000)

            await page.get_by_role("button", name="Μητρικός").click()
            await page.get_by_role("button", name="MasClub").click()
            await page.get_by_role("button", name="Δομή Ειδών Επ. 1").click()
            await page.get_by_role("button", name="Δομή Ειδών Επ. 2").click()
            await page.get_by_role("button", name="Δομή Ειδών Επ. 3").click()
            await page.get_by_role("button", name="Δομή Ειδών Επ. 4").click()
            await page.get_by_role("button", name="Πόλη").click()
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            await page.wait_for_timeout(60000)

            # ==== SCENARIO INTERACTIONS ====
            # Slicer interaction
            await page.get_by_role("group", name="Κατηγορίες Ειδών").locator("i").click()
            await page.get_by_role("treeitem", name="- ΦΡΕΣΚΑ ΠΡΟΙΟΝΤΑ").locator("span").first.click()
            await page.get_by_role("group", name="Κατηγορίες Ειδών").locator("i").click()
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            await page.wait_for_timeout(60000)
            #await page.get_by_role("button", name="Κατάστημα").click()
            

            # Filters
            await page.get_by_role("group", name="Καταστήματα").locator("i").click()
            await page.get_by_role("option", name="- ΚΡΥΣΤΑΛΛΗ 4").locator("div span").click()
            await page.get_by_role("option", name="- ΟΛΥΜΠΙΑΔΟΣ 113 & ΙΟΥΛΙΑΝΟΥ").locator("div span").click()
            await page.get_by_role("option", name="- ΙΩΑΝΝΙΔΟΥ 2 - ΠΑΝΟΡΑΜΑ").locator("div span").click()
            await page.get_by_role("option", name="- ΚΟΥΝΤΟΥΡΙΩΤΟΥ 43 - Ν.ΚΡΗΝΗ").locator("div span").click()
            await page.get_by_role("combobox", name="Sector").locator("i").click()
            await page.get_by_role("option", name="ΔΙΑΜΑΝΤΟΠΟΥΛΟΣ").locator("div span").click()
            await page.get_by_role("combobox", name="Manager3").locator("i").click()
            await page.get_by_role("option", name="ΔΡΕΠΑΣ").locator("div span").click()

            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            await page.wait_for_timeout(60000)


            # Clear Filters
            await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()

            # Date filter range
            # Match the correct format (after printing actual value)
            target_start_date = "18/08/2024"
            slider = page.locator('div[role="slider"][aria-label="Date"]').first

            await slider.focus()

            # Safety counter to prevent infinite loop
            max_attempts = 200
            attempts = 0

            while attempts < max_attempts:
                value = await slider.get_attribute("aria-valuetext")
                print(f"[Slider] Current: {value} | Target: {target_start_date}")
                
                if value == target_start_date:
                    break
                
                await slider.press("ArrowLeft")
                await page.wait_for_timeout(100)
                attempts += 1

            if attempts == max_attempts:
                print("⚠️ Reached maximum slider attempts. Target date not found.")

            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()



            # Clear Filters
            await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()


            # Drill actions
            await page.get_by_label("S3 - Πωλήσεις Ειδών από 01/01").get_by_test_id("visual-title").get_by_text("S3 - Πωλήσεις Ειδών από 01/01").click()
            await page.get_by_test_id("drill-down-level-grouped-btn").click()
            await page.wait_for_timeout(50000)
            await page.get_by_label("S3 - Πωλήσεις Ειδών από 01/01").get_by_test_id("visual-title").get_by_text("S3 - Πωλήσεις Ειδών από 01/01").click()
            await page.get_by_test_id("drill-up-level-btn").click()
            await page.wait_for_timeout(60000)

            # Clear Filters
            await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()
            await page.wait_for_timeout(60000)


            # Tab/Page switching
            await page.get_by_role("button", name="Σύγκριση Πωλήσεων").click()
             # Drill actions
            await page.get_by_label("S4 - Σύγκριση Πωλήσεις Ειδών").get_by_test_id("visual-title").get_by_text("S4 - Σύγκριση Πωλήσεις Ειδών").click()
            await page.get_by_test_id("drill-down-level-grouped-btn").click()
            await page.wait_for_timeout(50000)
            await page.get_by_label("S4 - Σύγκριση Πωλήσεις Ειδών").get_by_test_id("visual-title").get_by_text("S4 - Σύγκριση Πωλήσεις Ειδών").click()
            await page.get_by_test_id("drill-up-level-btn").click()
            await page.wait_for_timeout(60000)


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
