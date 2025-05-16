import asyncio
from playwright.async_api import async_playwright

PROFILE_DIR = "pbi_user_profile"  # Will store browser state and session
LOGIN_URL = "https://app.powerbi.com/groups/60451a2f-9965-4774-83ae-68d4a5a67d22/reports/48bc7fe0-8f62-4a67-964b-412e9754c572/ReportSection52325b70682a2cae3dad?experience=power-bi"

async def run():
    async with async_playwright() as p:
        print("Launching browser with persistent context...")
        browser = await p.chromium.launch_persistent_context(PROFILE_DIR, headless=False)
        page = await browser.new_page()

        print("Navigating to Power BI login page...")
        await page.goto(LOGIN_URL, timeout=60000)

        print(">> Manually log in. Once complete, close the browser window to save session.")
        await page.wait_for_timeout(60000)  # Wait time to log in manually

        # Keep browser open to store profile manually
        print("Waiting 2 more minutes before browser auto-closes...")
        await page.wait_for_timeout(120000)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
