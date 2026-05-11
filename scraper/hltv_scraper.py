import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

def create_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()

    # if headless, Chrome runs in the background, no window opens
    if headless:
        options.add_argument("--headless=new")

    # to prevent common issues on macOS/linux
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # spoof a User-Agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    # using webdriver_manager to auto-download the correct ChromeDriver version
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    return driver

def wait_for_element(driver: webdriver.Chrome, by: By, selector: str, timeout: int = 10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )

def dismiss_cookie_popup(driver: webdriver.Chrome):
    try:
        accept_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".CybotCookiebotDialogBodyButton"))
        )
        accept_btn.click()
        print("Cookie popup dismissed")
        time.sleep(1)
    except TimeoutException:
        print("No cookie popup found, continue")

def get_team_matches():
    ...