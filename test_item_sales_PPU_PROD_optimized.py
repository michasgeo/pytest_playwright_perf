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
REPORT_URL = 'https://app.powerbi.com/groups/me/reports/81da1739-d19f-447b-9460-a1f203e2dcfd/ReportSection52325b70682a2cae3dad?ctid=d9f147f4-090d-4444-a562-1cac43890a3d&experience=power-bi'

def get_user_credentials(user_id):
    username_key = f"PBI_USERNAME_{user_id}"
    password_key = f"PBI_PASSWORD_{user_id}"
    return os.getenv(username_key), os.getenv(password_key)

USER_IDS = list(range(1, 6))
NUM_USERS = len(USER_IDS)

THIS_FILE = Path(__file__).resolve()
TEST_NAME = THIS_FILE.stem
# Create a dedicated folder for this test file
TEST_FOLDER = THIS_FILE.parent / TEST_NAME
TEST_FOLDER.mkdir(parents=True, exist_ok=True)
# Each run gets its own timestamped subfolder
file_ts = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
RUN_FOLDER = TEST_FOLDER / f"run_{file_ts}"
RUN_FOLDER.mkdir(parents=True, exist_ok=True)

CSV_PATH = RUN_FOLDER / f"performance_logs.csv"
LOG_PATH = RUN_FOLDER / f"performance_debug.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_PATH, mode='w'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Helper functions for repeated actions
async def clear_filters(page, user_id):
    try:
        await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()
        await page.wait_for_timeout(5000)
        logger.info(f"[User {user_id}] 🧹 Filters cleared successfully.")
    except Exception as clear_err:
        logger.warning(f"[User {user_id}] ⚠️ 'Clear Filters' button not found or failed: {clear_err}")

async def reset_filters(page, user_id):
    try:
        await page.wait_for_selector("[data-testid='reset-to-default-btn']", timeout=5000)
        reset_btn = page.get_by_test_id("reset-to-default-btn")
        if await reset_btn.is_enabled():
            await reset_btn.click()
            await page.wait_for_selector("[data-testid='dailog-ok-btn']", timeout=5000)
            await page.get_by_test_id("dailog-ok-btn").click()
            logger.info(f"[User {user_id}] 🧹 Filters in the upper right corner have been reset successfully.")
        else:
            logger.info(f"[User {user_id}] ℹ️ Reset button is disabled, nothing to do.")
    except Exception as modal_err:
        logger.warning(f"[User {user_id}] ⚠️ Reset filters failed: {modal_err}")

async def deselect_dimensions(page, user_id):
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

# Write CSV header if file is new
def write_csv_header_if_new():
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "user_id", "status", "load_time_ms"])

@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", USER_IDS)
async def test_powerbi_load(user_id):
    write_csv_header_if_new()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(ignore_https_errors=True, bypass_csp=True,
                                            record_har_path=str(RUN_FOLDER / f"perf_{user_id}.har"),
                                            locale='en-US', user_agent='PlaywrightTestAgent')
        page = await context.new_page()
        page.set_default_navigation_timeout(120000)
        page.set_default_timeout(120000)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        USERNAME, PASSWORD = get_user_credentials(user_id)

        if not USERNAME or not PASSWORD:
            logger.error(f"❌ [User {user_id}] Missing credentials in environment variables.")
            with CSV_PATH.open("a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, user_id, "Missing credentials", "N/A"])
            return

        try:
            logger.info(f"[User {user_id}] Going to login URL...")
            await page.goto("https://app.powerbi.com/singleSignOn?experience=power-bi&ru=" + REPORT_URL)
            await page.get_by_role("textbox", name="Enter email").fill(USERNAME)
            await page.get_by_role("button", name="Submit").click()
            await page.get_by_role("textbox", name="Enter the password for").fill(PASSWORD)
            await page.get_by_role("button", name="Sign in").click()
            await page.get_by_role("button", name="Yes").click()

            await clear_filters(page, user_id)
            await deselect_dimensions(page, user_id)
            await reset_filters(page, user_id)

            # Interactions (shortened for brevity, add your scenario here)
            await page.get_by_role("button", name="Κατάστημα").click()
            await page.wait_for_timeout(5000)
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()
            await page.get_by_role("rowheader", name="Collapsed 101 - ΚΡΥΣΤΑΛΛΗ").get_by_label("Collapsed").click()
            await page.wait_for_timeout(10000)
            await page.get_by_role("button", name="Expanded").click()
            # ... (continue with your scenario as needed) ...

            # Example: Date slider logic (unchanged)
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
                await page.wait_for_timeout(100)
                attempts += 1
            if attempts == max_attempts:
                print("⚠️ Reached maximum slider attempts. Target date not found.")
            await page.get_by_role("group", name="Apply all slicers").locator("path").first.click()

            # ... (continue with your scenario as needed) ...

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
    logger.info(f"📝 Debug log saved to {LOG_PATH}")
