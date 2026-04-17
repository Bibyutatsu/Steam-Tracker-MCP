import requests
import os
from dotenv import load_dotenv

load_dotenv()

STEAM_WEB_API_KEY = os.getenv("STEAM_WEB_API_KEY")

def search_games(term, country_code="US", language="english"):
    """
    Searches the Steam store for games matching the term.
    """
    url = "https://store.steampowered.com/api/storesearch/"
    params = {
        "term": term,
        "l": language,
        "cc": country_code
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("total", 0) > 0:
            return data.get("items", [])
        return []
    except Exception as e:
        print(f"Error searching Steam store: {e}")
        return []

def get_app_details(appid, country_code="US", language="english"):
    """
    Retrieves detailed information (including precise pricing) for a specific app ID.
    """
    url = f"https://store.steampowered.com/api/appdetails"
    params = {
        "appids": appid,
        "cc": country_code,
        "l": language,
        "filters": "price_overview,basic"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        app_data = data.get(str(appid))
        if app_data and app_data.get("success"):
            return app_data.get("data")
        return None
    except Exception as e:
        print(f"Error fetching app details for {appid}: {e}")
        return None

def get_official_wishlist(steam_id):
    """
    Retrieves the wishlist AppIDs for a given Steam ID using the official IWishlistService.
    Requires STEAM_WEB_API_KEY.
    """
    if not STEAM_WEB_API_KEY:
        print("STEAM_WEB_API_KEY not found.")
        return []
        
    url = "https://api.steampowered.com/IWishlistService/GetWishlist/v1/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "steamid": steam_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("response", {}).get("items", [])
    except Exception as e:
        print(f"Error fetching official wishlist for {steam_id}: {e}")
        return []

def get_apps_details_batch(appids, country_code="US", language="english"):
    """
    Retrieves detailed information (including prices) for multiple app IDs.
    Returns a dictionary keyed by appid.
    Note: Performs individual requests as Steam store batch calls are unreliable.
    """
    results = {}
    for appid in appids:
        # Reusing single app details function
        data = get_app_details(appid, country_code=country_code, language=language)
        results[str(appid)] = {
            "success": True if data else False,
            "data": data
        }
    return results

def get_player_summaries(steam_ids):
    """
    Fetches basic profile information for a list of Steam IDs.
    """
    if not STEAM_WEB_API_KEY:
        print("STEAM_WEB_API_KEY not found.")
        return []
        
    url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "steamids": steam_ids
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("response", {}).get("players", [])
    except Exception as e:
        print(f"Error fetching player summaries: {e}")
        return []

def format_price(price_obj, currency=""):
    """
    Formats the price object (price_overview) into a human-readable string.
    """
    if not price_obj:
        return "Free / Not Available"
    
    # Handle standard price_overview object
    final_price = price_obj.get("final", price_obj.get("final_price", 0))
    curr = price_obj.get("currency", currency)
    
    if final_price == 0:
        return "Free"
        
    formatted_val = f"{final_price / 100:.2f}"
    return f"{formatted_val} {curr}"

if __name__ == "__main__":
    # Test search
    results = search_games("Age of Empires", "US")
    for item in results:
        name = item.get("name")
        price = item.get("price", {})
        print(f"Found: {name} (ID: {item.get('id')}) - Price: {format_price(price)}")
