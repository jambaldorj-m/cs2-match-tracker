import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager

HLTV_URL = "https://www.hltv.org/"

def _create_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()

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

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    return driver

def _dismiss_cookie_popup(driver: webdriver.Chrome) -> None:
    try:
        accept_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".CybotCookiebotDialogBodyButton"))
        )
        accept_btn.click()
        print("  [+] Cookie popup dismissed.")
        time.sleep(1)
    except TimeoutException:
        print("  [*] No cookie popup found, continuing...")

def _get_first_result(driver: webdriver.Chrome) -> WebElement | None:
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//td[@class='table-header']"))
        )

        results: list[WebElement] = driver.find_elements(
                By.XPATH,
                "(//td[contains(@class,'table-header') and (text()='Team' or text()='Event')]/following::td/a)[1]"
            )

        if not results:
            print("  [-] No matching search results found.")
            return None

        first = results[0]
        return first

    except TimeoutException:
        print("  [-] Search results did not load in time.")
        return None

def get_team_matches(team_name: str, headless: bool = False) -> list[dict]:
    driver = _create_driver(headless=headless)
    matches: list[dict] = []

    try:
        print(f"\n[*] Searching HLTV for: '{team_name}'")

        search_url = f"{HLTV_URL}search#query={team_name.replace(" ", "+")}"
        driver.get(search_url)
        print(f"  [+] Navigated to: {search_url}")

        _dismiss_cookie_popup(driver)

        result = _get_first_result(driver)
        if result is None:
            return []

        team_url: str | None = result.get_attribute("href")
        if not team_url:
            print("  [-] Selected team has no valid URL.")
            return []

        team_display_name: str = result.text.strip()

        matches_url = team_url + "#tab-matchesBox"
        driver.get(matches_url)
        print("  [+] Loading team matches page...")

        time.sleep(2)
        _dismiss_cookie_popup(driver)

        try:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".matchesTable"))
            )
        except TimeoutException:
            print("  [-] Matches table did not load in time.")
            return []

        match_rows: list[WebElement] = driver.find_elements(By.CSS_SELECTOR, ".upcomingMatch")

        if not match_rows:
            print(f"  [*] No upcoming matches found for '{team_display_name}'.")
            return []

        print(f"  [+] Found {len(match_rows)} upcoming match(es). Extracting data...\n")

        for row in match_rows:
            try:
                team1: str = row.find_element(By.CSS_SELECTOR, ".matchTeam.team1 .matchTeamName").text.strip()
                team2: str = row.find_element(By.CSS_SELECTOR, ".matchTeam.team2 .matchTeamName").text.strip()
                event: str = row.find_element(By.CSS_SELECTOR, ".matchEvent .matchEventName").text.strip()
                date: str  = row.find_element(By.CSS_SELECTOR, ".matchTime").text.strip()

                match_url: str | None = row.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                if not match_url:
                    continue

                matches.append({
                    "team1": team1,
                    "team2": team2,
                    "event": event,
                    "date": date,
                    "match_url": match_url,
                })

            except NoSuchElementException as e:
                print(f"  [!] Skipped a row due to missing element: {e}")
                continue

    finally:
        driver.quit()
        print("\n[*] Browser closed.")

    return matches

def get_tournament_matches(tournament_name: str, headless: bool = False) -> list[dict]:
    driver = _create_driver(headless=headless)
    matches: list[dict] = []
    event_display_name: str = tournament_name

    try:
        print(f"\n[*] Searching HLTV for tournament: '{tournament_name}'")

        search_url = f"{HLTV_URL}search#query={tournament_name.replace(" ", "+")}"
        driver.get(search_url)
        _dismiss_cookie_popup(driver)

        selected = _get_first_result(driver)
        if selected is None:
            return []

        event_url: str | None = selected.get_attribute("href")
        if not event_url:
            print("  [-] Selected tournament has no valid URL.")
            return []

        event_display_name = selected.text.strip()

        driver.get(event_url)
        time.sleep(2)
        _dismiss_cookie_popup(driver)

        try:
            WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".matchday"))
            )
        except TimeoutException:
            print("  [-] Match schedule did not load.")
            return []

        match_rows = driver.find_elements(By.CSS_SELECTOR, ".matchday .match a.matchRowLink")
        print(f"  [+] Found {len(match_rows)} match(es). Extracting...\n")

        for row in match_rows:
            try:
                team1 = row.find_element(By.CSS_SELECTOR, ".matchTeams span:nth-child(1)").text.strip()
                team2 = row.find_element(By.CSS_SELECTOR, ".matchTeams span:nth-child(3)").text.strip()
                date  = row.find_element(By.CSS_SELECTOR, ".matchTime").text.strip()

                row_url: str | None = row.get_attribute("href")
                if not row_url:
                    continue

                matches.append({
                    "team1": team1,
                    "team2": team2,
                    "event": event_display_name,
                    "date": date,
                    "match_url": row_url,
                })

            except NoSuchElementException:
                continue

    finally:
        driver.quit()
        print("\n[*] Browser closed.")

    return matches

def print_matches(matches: list[dict], label: str = "Upcoming Matches") -> None:
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")

    for i, match in enumerate(matches, start=1):
        print(f"\n  Match {i}:")
        print(f"    {match['team1']}  vs  {match['team2']}")
        print(f"    Event : {match['event']}")
        print(f"    Date  : {match['date']}")
        print(f"    Link  : {match['match_url']}")

    print(f"\n{'='*50}\n")