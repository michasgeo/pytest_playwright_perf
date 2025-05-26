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
REPORT_URL = 'https://app.powerbi.com/groups/me/reports/c7b293b1-9eae-4e4f-ac4a-98684309e91b/4368c5bccd3672c1b070?ctid=d9f147f4-090d-4444-a562-1cac43890a3d&experience=power-bi'

def get_user_credentials(user_id):
    username_key = f"PBI_USERNAME_{user_id}"
    password_key = f"PBI_PASSWORD_{user_id}"
    return os.getenv(username_key), os.getenv(password_key)

CSV_FILENAME = "performance_log"
LOG_FILENAME = "performance_debug.log"

# TODO: Here the number of users can be adjusted
USER_IDS = list(range(1, 6))
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

            #Clear Filters
            logger.info(f"[User {user_id}] Clearing any pre-applied filters...")
            try:
                await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()
                await page.wait_for_timeout(10000)
                logger.info(f"[User {user_id}] 🧹 Filters cleared successfully.")
            except Exception as clear_err:
                logger.warning(f"[User {user_id}] ⚠️ 'Clear Filters' button not found or failed: {clear_err}")

            
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
            #select day
            await page.get_by_role("combobox", name="insert_date").locator("i").click()
            await page.get_by_role("option", name="26/05/").locator("div span").click()
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
          
            #bar selection
            # await page.get_by_role("option", name="Φυλλάδιο Λιανικής 248455 (38.55%)").click()
            # await page.get_by_role("option", name="Φυλλάδιο Λιανικής 248455 (38.55%)").click()
            

            # Filters
            #select hour 
            await page.get_by_role("group", name="Επιλογή Ώρας").locator("i").click()
            await page.get_by_role("option", name="08:00").locator("div span").click()
            await page.get_by_role("option", name="08:30").locator("div span").click()
            await page.get_by_role("option", name="09:00").locator("div span").click()
            await page.get_by_role("option", name="09:30").locator("div span").click()
            await page.get_by_role("option", name="10:00").locator("div span").click()
            await page.get_by_role("group", name="Επιλογή Ώρας").locator("i").click()
            await page.wait_for_timeout(5000)

            #other filters
            await page.get_by_role("group", name="Ομάδα ειδών").locator("i").click()
            await page.get_by_role("option", name="- ΜΗ ΑΛΛΟΙΩΣΙΜΑ").locator("div span").click()
            await page.get_by_role("group", name="Ομάδα ειδών").locator("i").click()

            await page.get_by_role("combobox", name="bulk_id_description").locator("i").click()
            await page.get_by_role("option", name="Λιανική", exact=True).locator("div span").click()
            await page.get_by_role("combobox", name="bulk_id_description").locator("i").click()

            #apply
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            await page.wait_for_timeout(5000)


            # Clear Filters
            await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()
            await page.wait_for_timeout(5000)

            #reset
            await page.get_by_test_id("reset-to-default-btn").click()
            await page.wait_for_timeout(5000)
            await page.get_by_test_id("dailog-ok-btn").click()


            #change tab
            await page.get_by_role("tab", name="Συγκριτικός Πίνακας").click()

            #select day
            await page.get_by_role("combobox", name="insert_date").locator("i").click()
            await page.get_by_role("option", name="26/05/").locator("div span").click()
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            await page.wait_for_timeout(5000)

            #interact with bars
            await page.get_by_role("button", name="Αγοραστής").click()
            await page.get_by_role("button", name="Family").click()
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            await page.get_by_role("button", name="Αγοραστής").click()
            await page.get_by_role("button", name="Family").click()
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()

            #await page.locator('div[role="rowheader"]', has_text="11ο χλμ Θεσσαλονίκης – Ωραιοκάστρου")
            await page.get_by_test_id("visual-container-repeat").get_by_text("ο χλμ Θεσσαλονίκης – Ωραιοκάστρου").click()
            #await page.locator('div[role="rowheader"]', has_text="11ο χλμ Θεσσαλονίκης – Ωραιοκάστρου")

            await page.get_by_role("rowheader", name="Γ - ΑΓΟΡΑΣΤΗΣ MrGRAND").click()
            await page.get_by_role("rowheader", name="Γ - ΑΓΟΡΑΣΤΗΣ MrGRAND Selected").click()

            #filters
            await page.get_by_role("group", name="Επιλογή Ώρας").locator("i").click()
            await page.get_by_role("option", name="08:00").locator("div span").click()
            await page.get_by_role("option", name="08:30").locator("div span").click()
            await page.get_by_role("option", name="09:00").locator("div span").click()
            await page.get_by_role("option", name="09:30").locator("div span").click()
            await page.get_by_role("option", name="10:00").locator("div span").click()
            await page.get_by_role("group", name="Επιλογή Ώρας").locator("i").click()


            await page.get_by_role("combobox", name="county").locator("i").click()
            await page.get_by_role("option", name="ΑΤΤΙΚΗ").locator("div span").click()
            await page.get_by_role("combobox", name="county").locator("i").click()

            await page.get_by_role("group", name="Αγοραστής").locator("i").click()
            await page.get_by_role("option", name="- ΑΓΟΡΑΣΤΗΣ ΜΑΝΑΒΙΚΩΝ").locator("div span").click()
            await page.get_by_role("group", name="Αγοραστής").locator("i").click()


            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()



            # Clear Filters
            await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()


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
