
import asyncio
import os
import csv
import time
import logging
from datetime import datetime
import pytest
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
REPORT_URL = 'https://app.powerbi.com/groups/60451a2f-9965-4774-83ae-68d4a5a67d22/reports/48bc7fe0-8f62-4a67-964b-412e9754c572/ReportSection52325b70682a2cae3dad?experience=power-bi'
USERNAME = os.getenv("PBI_USERNAME")
PASSWORD = os.getenv("PBI_PASSWORD")

CSV_FILENAME = "performance_log.csv"
LOG_FILENAME = "performance_debug.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILENAME, mode='w'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
results = []

@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", range(1, 6))  # Simulate 5 users
async def test_powerbi_load(user_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = time.time()

        try:
            logger.info(f"[User {user_id}] Going to login URL...")
            await page.goto("https://app.powerbi.com/singleSignOn?experience=power-bi&ru=https%3A%2F%2Fapp.powerbi.com%2Fgroups%2F60451a2f-9965-4774-83ae-68d4a5a67d22%2Freports%2F48bc7fe0-8f62-4a67-964b-412e9754c572%2FReportSection52325b70682a2cae3dad%3Fexperience%3Dpower-bi%26noSignUpCheck%3D1")

            await page.get_by_role("textbox", name="Enter email").click()
            await page.get_by_role("textbox", name="Enter email").fill(USERNAME)
            await page.get_by_role("button", name="Submit").click()
            await page.get_by_role("textbox", name="Enter the password for").click()
            await page.get_by_role("textbox", name="Enter the password for").fill(PASSWORD)
            await page.get_by_role("button", name="Sign in").click()
            await page.get_by_role("button", name="Yes").click()

            try:
                await page.wait_for_selector('input[id="idBtn_Back"]', timeout=5000)
                await page.click('input[id="idBtn_Back"]')
            except:
                pass

            logger.info(f"[User {user_id}] Navigating to report...")
            await page.goto(REPORT_URL, timeout=60000)

            # NEW: wait until the page finishes network activity
            await page.wait_for_load_state("networkidle", timeout=60000)

            # Optional screenshot before check
            await page.screenshot(path=f"user_{user_id}_before_visual_check.png")

            # NEW: wait for visual container to become available
            await page.wait_for_selector("css=div.visual-container >> nth=0", timeout=30000)

            load_time_ms = round((time.time() - start_time) * 1000)
            logger.info(f"✅ [User {user_id}] Loaded in {load_time_ms} ms")
            results.append([timestamp, user_id, "Success", load_time_ms])
        except Exception as e:
            await page.screenshot(path=f"user_{user_id}_error.png")
            logger.error(f"❌ [User {user_id}] Failed: {e}")
            results.append([timestamp, user_id, f"Failed: {str(e)}", "N/A"])
        finally:
            await browser.close()

def teardown_module(module):
    with open(CSV_FILENAME, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "User ID", "Status", "Load Time (ms)"])
        writer.writerows(results)
    logger.info(f"📄 Results saved to {CSV_FILENAME}")
    logger.info(f"📝 Debug log saved to {LOG_FILENAME}")
