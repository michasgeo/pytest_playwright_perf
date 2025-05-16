
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

REPORT_URL = os.getenv("PBI_REPORT_URL")  # Put your full report URL in .env
TOTAL_USERS = int(os.getenv("PBI_USER_COUNT", 5))  # Default to 5 if not set

CSV_FILENAME = "performance_pool_log.csv"
LOG_FILENAME = "performance_pool_debug.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILENAME, mode="w"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
results = []

def get_user_credentials(index):
    username = os.getenv(f"PBI_USERNAME_{index}")
    password = os.getenv(f"PBI_PASSWORD_{index}")
    if not username or not password:
        raise ValueError(f"Missing credentials for user {index}")
    return username, password

@pytest.mark.asyncio
@pytest.mark.parametrize("user_index", range(1, TOTAL_USERS + 1))
async def test_powerbi_user_pool_load(user_index):
    username, password = get_user_credentials(user_index)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        start_time = time.time()

        try:
            logger.info(f"[User {user_index}] Logging in as {username}...")
            await page.goto(f"https://app.powerbi.com/singleSignOn?experience=power-bi&ru={REPORT_URL}", timeout=60000)

            await page.get_by_role("textbox", name="Enter email").fill(username)
            await page.get_by_role("button", name="Submit").click()
            await page.get_by_role("textbox", name="Enter the password for").fill(password)
            await page.get_by_role("button", name="Sign in").click()

            try:
                await page.get_by_role("button", name="Yes").click()
            except:
                pass

            try:
                await page.wait_for_selector('input[id="idBtn_Back"]', timeout=5000)
                await page.click('input[id="idBtn_Back"]')
            except:
                pass

            response = await page.goto(REPORT_URL, timeout=60000)
            assert response.status == 200, f"Failed to load report: {response.status}"
            await page.wait_for_selector("div.visual-container", timeout=60000)

            load_time_ms = round((time.time() - start_time) * 1000)
            logger.info(f"✅ [User {user_index}] Report loaded in {load_time_ms} ms")
            results.append([timestamp, user_index, username, "Success", load_time_ms])

        except Exception as e:
            logger.error(f"❌ [User {user_index}] Failed: {e}")
            await page.screenshot(path=f"user_{user_index}_error.png")
            results.append([timestamp, user_index, username, f"Failed: {e}", "N/A"])
        finally:
            await browser.close()

def teardown_module(module):
    with open(CSV_FILENAME, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "User Index", "Username", "Status", "Load Time (ms)"])
        writer.writerows(results)
    logger.info(f"📄 Results saved to {CSV_FILENAME}")
    logger.info(f"📝 Debug log saved to {LOG_FILENAME}")
