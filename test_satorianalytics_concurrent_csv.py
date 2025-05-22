
import os
import time
import csv
import logging
from datetime import datetime
import pytest
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

TOTAL_USERS = int(os.getenv("PBI_USER_COUNT", 5))
REPORT_URL = os.getenv("PBI_REPORT_URL", "https://www.satorianalytics.com/")
CSV_FILENAME = "user_test_results.csv"
LOG_FILENAME = "test_run_debug.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILENAME, mode="w"), logging.StreamHandler()]
)

logger = logging.getLogger(__name__)
results = []

def get_user_credentials(index):
    username = os.getenv(f"PBI_USERNAME_USER{index}")
    password = os.getenv(f"PBI_PASSWORD_USER{index}")
    if not username or not password:
        raise ValueError(f"Missing credentials for user {index}")
    return username, password

@pytest.mark.parametrize("user_index", range(1, TOTAL_USERS + 1))
def test_satorianalytics_navigation_concurrent(user_index):
    from playwright.sync_api import sync_playwright
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start = time.time()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            page.goto(REPORT_URL)

            page.locator("#nav-item-solutions").get_by_text("Solutions").click()
            try:
                page.get_by_role("button", name="Close banner").click(timeout=3000)
            except:
                logger.info(f"[User {user_index}] No banner to close.")

            assert "Satori" in page.title()

            duration = round((time.time() - start) * 1000)
            results.append({
                "Timestamp": timestamp,
                "User": user_index,
                "Status": "Success",
                "Load Time (ms)": duration
            })

            logger.info(f"[User {user_index}] ✅ Success in {duration} ms")

            context.close()
            browser.close()

    except Exception as e:
        results.append({
            "Timestamp": timestamp,
            "User": user_index,
            "Status": f"Failed: {e}",
            "Load Time (ms)": "N/A"
        })
        logger.error(f"[User {user_index}] ❌ Failed: {e}")

def teardown_module(module):
    with open(CSV_FILENAME, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Timestamp", "User", "Status", "Load Time (ms)"])
        writer.writeheader()
        writer.writerows(results)
    logger.info(f"📄 CSV results written to {CSV_FILENAME}")
