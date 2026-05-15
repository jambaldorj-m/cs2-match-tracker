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

HLTV_URL = "https://www.hltv.org"
WAIT_TIME = 10

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

def _get_first_result(driver: webdriver.Chrome) -> WebElement | None:
    try:
        WebDriverWait(driver, WAIT_TIME).until(
            EC.presence_of_element_located((By.XPATH, "//td[@class='table-header']"))
        )

        results: list[WebElement] = driver.find_elements(
            By.XPATH,
            "(//td[contains(@class,'table-header') and (text()='Team' or text()='Event')]/following::td/a)[1]"
        )

        if not results:
            print("  [-] No matching search results found.")
            return None

        return results[0]

    except TimeoutException:
        print("  [-] Search results did not load in time.")
        return None

def _extract_team_matches(driver: webdriver.Chrome, display_name: str) -> list[dict]:
    matches: list[dict] = []

    try:
        WebDriverWait(driver, WAIT_TIME).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".table-container.match-table"))
        )
    except TimeoutException:
        print("  [-] Matches table did not load in time.")
        return []

    match_rows: list[WebElement] = driver.find_elements(
        By.CSS_SELECTOR, ".table-container.match-table tbody tr.team-row"
    )

    if not match_rows:
        print(f"  [*] No upcoming matches found for '{display_name}'.")
        return []

    print(f"  [+] Found {len(match_rows)} upcoming match(es). Extracting data...\n")

    for row in match_rows:
        try:
            date: str = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()

            team_links: list[WebElement] = row.find_elements(By.CSS_SELECTOR, "td:nth-child(2) a[href*='/team/']")
            if len(team_links) < 2:
                continue

            team1: str = team_links[0].text.strip()
            team2: str = team_links[1].text.strip()

            event_els: list[WebElement] = row.find_elements(
                By.XPATH,
                "./preceding-sibling::tr[contains(@class,'tr-seperator')][1]/td/a"
            )
            event: str = event_els[0].text.strip() if event_els else "Unknown Event"

            match_url: str | None = row.find_element(
                By.CSS_SELECTOR, "td a[href*='/matches/']"
            ).get_attribute("href")
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

    return matches

def _extract_tournament_matches(driver: webdriver.Chrome, event_display_name: str) -> list[dict]:
    matches: list[dict] = []

    try:
        WebDriverWait(driver, WAIT_TIME).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".matchday"))
        )
    except TimeoutException:
        print("  [-] Match schedule did not load.")
        return []

    match_rows: list[WebElement] = driver.find_elements(
        By.CSS_SELECTOR, ".matchday .match a.matchRowLink"
    )

    if not match_rows:
        print(f"  [*] No matches found for '{event_display_name}'.")
        return []

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

    return matches

def get_team_matches(team_name: str, headless: bool = False) -> list[dict]:
    driver = _create_driver(headless=headless)

    try:
        print(f"\n[*] Searching HLTV for team: '{team_name}'")

        search_url = f"{HLTV_URL}/search#query={team_name.replace(' ', '+')}"
        driver.get(search_url)
        print(f"  [+] Navigated to: {search_url}")

        result = _get_first_result(driver)
        if result is None:
            return []

        team_url: str | None = result.get_attribute("href")
        if not team_url:
            print("  [-] Selected team has no valid URL.")
            return []

        team_display_name: str = result.text.strip()
        print(f"  [+] Found: '{team_display_name}'")

        driver.get(team_url + "#tab-matchesBox")
        print("  [+] Loading team matches page...")
        time.sleep(2)

        return _extract_team_matches(driver, team_display_name)

    finally:
        driver.quit()
        print("\n[*] Browser closed.")


def get_tournament_matches(tournament_name: str, headless: bool = False) -> list[dict]:
    driver = _create_driver(headless=headless)

    try:
        print(f"\n[*] Searching HLTV for tournament: '{tournament_name}'")

        search_url = f"{HLTV_URL}/search#query={tournament_name.replace(' ', '+')}"
        driver.get(search_url)
        print(f"  [+] Navigated to: {search_url}")

        result = _get_first_result(driver)
        if result is None:
            return []

        event_url: str | None = result.get_attribute("href")
        if not event_url:
            print("  [-] Selected tournament has no valid URL.")
            return []

        event_display_name: str = result.text.strip()
        print(f"  [+] Found: '{event_display_name}'")

        driver.get(event_url)
        time.sleep(2)

        return _extract_tournament_matches(driver, event_display_name)

    finally:
        driver.quit()
        print("\n[*] Browser closed.")

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