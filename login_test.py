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
LOG_FILENAME = "performance_debug.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILENAME, mode='w'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
results = []

@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", range(1, 71))  # Simulate 70 users
async def test_powerbi_load(user_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
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


            try:
                await page.wait_for_selector('input[id="idBtn_Back"]', timeout=5000)
                await page.click('input[id="idBtn_Back"]')
            except:
                pass

            logger.info(f"[User {user_id}] Navigating to report...")
            await page.goto(REPORT_URL, timeout=80000)
            await page.wait_for_selector("div.visual-container")

        except Exception as e:
            logger.error(f"❌ [User {user_id}] Failed: {e}")
            results.append([timestamp, user_id, f"Failed: {str(e)}", "N/A"])

        finally:
            await browser.close()


def teardown_module(module):
    with open(CSV_FILENAME, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "User ID", "Status", "Load Time (ms)"])
        writer.writerows(results)
    logger.info(f"📄 Results saved to {CSV_FILENAME}")
    logger.info(f"📝 Debug log saved to {LOG_FILENAME}")