import os
from dotenv import load_dotenv
from steam_api import search_games, format_price, get_official_wishlist, get_player_summaries, get_apps_details_batch
from utils import get_country_code

load_dotenv()
STEAM_ID = os.getenv("STEAM_ID")

def test_flow():
    cc = get_country_code()
    print(f"Detected Country Code: {cc}\n")
    
    # Test 1: Search
    query = "Age of Empires"
    print(f"Searching for: {query}")
    results = search_games(query, country_code=cc)
    if results:
        top = results[0]
        print(f"- Found {len(results)} matches. Top result: {top.get('name')} (ID: {top.get('id')})")
    
    # Test 2: Player Summary
    if STEAM_ID:
        print(f"\nFetching profile for STEAM_ID: {STEAM_ID}")
        players = get_player_summaries(STEAM_ID)
        if players:
            p = players[0]
            print(f"- Persona Name: {p.get('personaname')}")
    
    # Test 3: Official Wishlist
    if STEAM_ID:
        print(f"\nFetching official wishlist for STEAM_ID: {STEAM_ID}")
        wishlist_items = get_official_wishlist(STEAM_ID)
        if wishlist_items:
            print(f"- Found {len(wishlist_items)} items on wishlist.")
            appids = [item.get("appid") for item in wishlist_items[:3]]
            print(f"- Fetching prices for top 3: {appids}")
            details = get_apps_details_batch(appids, country_code=cc)
            for aid, res in details.items():
                if res.get("success"):
                    name = res.get("data", {}).get("name")
                    price = res.get("data", {}).get("price_overview", {}).get("final_formatted", "N/A")
                    print(f"  - {name}: {price}")
        else:
            print("- No wishlist items found or API error.")

if __name__ == "__main__":
    test_flow()
