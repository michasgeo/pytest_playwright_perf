# Shared pytest_asyncio fixtures could go here
import pytest_asyncio
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment variables from .env
load_dotenv("users.env")

@pytest_asyncio.fixture(scope="session")
async def browser_context():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    yield context
    await context.close()
    await browser.close()
    await playwright.stop()


@pytest_asyncio.fixture(scope="function")
def credentials(request):
    user_id = request.param
    username_key = f"PBI_USERNAME_{user_id}"
    password_key = f"PBI_PASSWORD_{user_id}"
    return {
        "username": os.getenv(username_key),
        "password": os.getenv(password_key)
    }



@pytest_asyncio.fixture(scope="function")
def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
