from scraper.hltv_scraper import get_team_matches, get_tournament_matches, print_matches

def main() -> None:
    print("\nWhat would you like to search?")
    print("  1. Upcoming matches for a team")
    print("  2. Matches in a tournament")

    option = input("Enter option (1/2): ").strip().lower()

    match option:
        case "1":
            team = input("Enter team name (e.g. FaZe, NaVi, G2): ").strip()
            if not team:
                print("No team name entered.")
                return
            matches = get_team_matches(team, headless=False)
            print_matches(matches, label=f"Upcoming Matches - {team}")

        case "2":
            tournament = input("Enter tournament name (e.g. PGL Major 2025): ").strip()
            if not tournament:
                print("No tournament name entered.")
                return
            matches = get_tournament_matches(tournament, headless=False)
            print_matches(matches, label=f"Matches - {tournament}")

        case _:
            print("Invalid option.")

if __name__ == "__main__":
    main()