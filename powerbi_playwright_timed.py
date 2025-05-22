import asyncio
import os
import csv
import time
import logging
from datetime import datetime
import pytest
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv("users.env")
REPORT_URL = 'https://app.powerbi.com/groups/3081326c-54e1-426e-a4df-bffb371061fa/reports/624c61a6-880f-445a-a9c1-6d08294bace1/ReportSection52325b70682a2cae3dad?experience=fabric-developer&clientSideAuth=0&bookmarkGuid=0bd1be94a0d3bb5d4302'

def get_user_credentials(user_id):
    username_key = f"PBI_USERNAME_{user_id}"
    password_key = f"PBI_PASSWORD_{user_id}"
    return os.getenv(username_key), os.getenv(password_key)

CSV_FILENAME = "performance_log.csv"
TIMING_FILENAME = "interaction_timings.csv"
LOG_FILENAME = "performance_debug.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILENAME, mode='w'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def log_step_time(writer, timestamp, user_id, step_name, start, end):
    duration_ms = round((end - start) * 1000)
    writer.writerow([timestamp, user_id, step_name, duration_ms])
    logger.info(f"[User {user_id}] ⏱️ Step '{step_name}' took {duration_ms} ms")

@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", range(1, 11))  # Simulate 10 users
async def test_powerbi_load(user_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()
        USERNAME, PASSWORD = get_user_credentials(user_id)

        with open(CSV_FILENAME, mode="a", newline="", encoding="utf-8") as result_file, \
             open(TIMING_FILENAME, mode="a", newline="", encoding="utf-8") as timing_file:

            result_writer = csv.writer(result_file)
            timing_writer = csv.writer(timing_file)

            if not USERNAME or not PASSWORD:
                logger.error(f"❌ [User {user_id}] Missing credentials.")
                result_writer.writerow([timestamp, user_id, "Missing credentials", "N/A"])
                return

            try:
                logger.info(f"[User {user_id}] Starting login...")

                t0 = time.time()
                await page.goto("https://app.powerbi.com/singleSignOn?experience=power-bi&ru=" + REPORT_URL)
                await page.get_by_role("textbox", name="Enter email").fill(USERNAME)
                await page.get_by_role("button", name="Submit").click()
                await page.get_by_role("textbox", name="Enter the password for").fill(PASSWORD)
                await page.get_by_role("button", name="Sign in").click()
                await page.get_by_role("button", name="Yes").click()
                t1 = time.time()
                log_step_time(timing_writer, timestamp, user_id, "Login", t0, t1)

                logger.info(f"[User {user_id}] Clearing filters...")
                t0 = time.time()
                try:
                    await page.locator("visual-modern").filter(has_text="Clear Filters").locator("path").first.click()
                    await page.wait_for_timeout(1500)
                except Exception:
                    logger.warning(f"[User {user_id}] ⚠️ Clear Filters not found.")
                t1 = time.time()
                log_step_time(timing_writer, timestamp, user_id, "Clear Filters", t0, t1)

                logger.info(f"[User {user_id}] Deselecting dimensions...")
                t0 = time.time()
                selected_paths = page.locator('path.sub-selectable.selected')
                count = await selected_paths.count()
                for i in range(count):
                    await selected_paths.nth(i).click()
                t1 = time.time()
                log_step_time(timing_writer, timestamp, user_id, "Deselect Dimensions", t0, t1)

                logger.info(f"[User {user_id}] Interacting with slicers and filters...")
                t0 = time.time()
                await page.get_by_role("button", name="Κατάστημα").click()
                await page.get_by_role("rowheader", name="Collapsed 101 - ΚΡΥΣΤΑΛΛΗ").get_by_label("Collapsed").click()
                await page.get_by_role("button", name="Expanded").click()
                await page.get_by_role("button", name="MasClub").click()
                await page.get_by_role("button", name="Μήνας").click()
                await page.get_by_role("button", name="Δομή Ειδών Επ. 1").click()
                await page.get_by_role("button", name="Πόλη").click()
                t1 = time.time()
                log_step_time(timing_writer, timestamp, user_id, "Slicer Filters", t0, t1)

                logger.info(f"[User {user_id}] Applying Date Range...")
                t0 = time.time()
                target_start_date = "18/08/2024"
                slider = page.locator('div[role="slider"][aria-label="Date"]').first
                await slider.focus()
                for _ in range(200):
                    value = await slider.get_attribute("aria-valuetext")
                    if value == target_start_date:
                        break
                    await slider.press("ArrowLeft")
                    await page.wait_for_timeout(100)
                t1 = time.time()
                log_step_time(timing_writer, timestamp, user_id, "Slider Date", t0, t1)

                logger.info(f"[User {user_id}] Drill interactions...")
                t0 = time.time()
                await page.get_by_label("S3 - Πωλήσεις Ειδών από 01/01").get_by_test_id("visual-title").get_by_text("S3 - Πωλήσεις Ειδών από 01/01").click()
                await page.get_by_test_id("drill-down-level-grouped-btn").click()
                await page.get_by_label("S3 - Πωλήσεις Ειδών από 01/01").get_by_test_id("visual-title").get_by_text("S3 - Πωλήσεις Ειδών από 01/01").click()
                await page.get_by_test_id("drill-up-level-btn").click()
                t1 = time.time()
                log_step_time(timing_writer, timestamp, user_id, "Drill Actions", t0, t1)

                load_time_ms = round((time.time() - start_time) * 1000)
                result_writer.writerow([timestamp, user_id, "Success", load_time_ms])
                logger.info(f"✅ [User {user_id}] Test completed in {load_time_ms} ms")

            except Exception as e:
                logger.error(f"❌ [User {user_id}] Failed: {e}")
                result_writer.writerow([timestamp, user_id, f"Failed: {str(e)}", "N/A"])
            finally:
                await browser.close()
