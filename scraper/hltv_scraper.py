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

def wait_for_element(driver: webdriver.Chrome, by: str, selector: str, timeout: int = 10) -> WebElement:
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )

def dismiss_cookie_popup(driver: webdriver.Chrome) -> None:
    try:
        accept_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".CybotCookiebotDialogBodyButton"))
        )
        accept_btn.click()
        print("  [+] Cookie popup dismissed.")
        time.sleep(1)
    except TimeoutException:
        print("  [*] No cookie popup found, continuing...")

def get_team_matches(team_name: str, headless: bool = False) -> list[dict]:
    driver = create_driver(headless=headless)
    matches: list[dict] = []

    try:
        print(f"\n[*] Searching HLTV for: '{team_name}'")

        # navigate to HLTV team search
        search_url = f"https://www.hltv.org/search#query={team_name.replace(' ', '%20')}"
        driver.get(search_url)
        print(f"  [+] Navigated to: {search_url}")

        dismiss_cookie_popup(driver)

        # find the team link in search results
        try:
            team_link: WebElement = wait_for_element(
                driver,
                By.CSS_SELECTOR,
                ".result-con .team a",
                timeout=10
            )
            # get_attribute returns str | None
            team_url: str | None = team_link.get_attribute("href")
            if not team_url:
                print(f"  [-] Found team element but href was empty.")
                return []

            team_display_name: str = team_link.text.strip()
            print(f"  [+] Found: '{team_display_name}' -> {team_url}")

        except TimeoutException:
            print(f"  [-] Could not find '{team_name}' on HLTV.")
            return []

        # navigate to the team's matches tab
        # team_url is guaranteed str here (None check above)
        matches_url = team_url + "#tab-matchesBox"
        driver.get(matches_url)
        print("  [+] Loading team matches page...")

        # human-like delay to avoid triggering bot detection
        time.sleep(2)
        dismiss_cookie_popup(driver)

        # wait for the matches table to load
        try:
            wait_for_element(
                driver,
                By.CSS_SELECTOR,
                ".matchesTable",
                timeout=12
            )
        except TimeoutException:
            print("  [-] Matches table did not load in time.")
            return []

        match_rows: list[WebElement] = driver.find_elements(By.CSS_SELECTOR, ".upcomingMatch")

        if not match_rows:
            print(f"  [*] No upcoming matches found for '{team_display_name}'.")
            return []

        print(f"  [+] Found {len(match_rows)} upcoming match(es). Extracting data...\n")

        # extract data from each match row
        for row in match_rows:
            try:
                team1: str = row.find_element(By.CSS_SELECTOR, ".matchTeam.team1 .matchTeamName").text.strip()
                team2: str = row.find_element(By.CSS_SELECTOR, ".matchTeam.team2 .matchTeamName").text.strip()
                event: str = row.find_element(By.CSS_SELECTOR, ".matchEvent .matchEventName").text.strip()
                date: str  = row.find_element(By.CSS_SELECTOR, ".matchTime").text.strip()

                # get_attribute returns str | None
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
    driver = create_driver(headless=headless)
    matches: list[dict] = []
    event_display_name: str = tournament_name  # fallback if scraping fails

    try:
        print(f"\n[*] Searching HLTV for tournament: '{tournament_name}'")

        search_url = f"https://www.hltv.org/search#query={tournament_name.replace(' ', '%20')}"
        driver.get(search_url)
        dismiss_cookie_popup(driver)

        # find the event/tournament link in search results
        try:
            event_link: WebElement = wait_for_element(
                driver,
                By.CSS_SELECTOR,
                ".result-con .event a",
                timeout=10
            )
            # guard against None before passing to driver.get()
            event_url: str | None = event_link.get_attribute("href")
            if not event_url:
                print("  [-] Found event element but href was empty.")
                return []

            event_display_name = event_link.text.strip()
            print(f"  [+] Found event: '{event_display_name}' -> {event_url}")

        except TimeoutException:
            print(f"  [-] Could not find tournament '{tournament_name}' on HLTV.")
            return []

        # event_url is guaranteed str here
        driver.get(event_url)
        time.sleep(2)
        dismiss_cookie_popup(driver)

        # wait for match schedule to load
        try:
            wait_for_element(driver, By.CSS_SELECTOR, ".matchday", timeout=12)
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

    if not matches:
        print("  No matches to display.")
        return

    for i, match in enumerate(matches, start=1):
        print(f"\n  Match {i}:")
        print(f"    {match['team1']}  vs  {match['team2']}")
        print(f"    Event : {match['event']}")
        print(f"    Date  : {match['date']}")
        print(f"    Link  : {match['match_url']}")

    print(f"\n{'='*50}\n")