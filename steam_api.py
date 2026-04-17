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

def format_price(price_obj):
    """
    Formats the price object from storesearch or appdetails into a human-readable string.
    """
    if not price_obj:
        return "Free / Not Available"
    
    currency = price_obj.get("currency", "")
    final_price = price_obj.get("final", 0)
    
    # Steam prices are usually in subunits (e.g. cents)
    # However, storesearch returns 'final' as an integer but it seems to be in cents
    # Let's verify this in the test phase. Usually it's divided by 100.
    
    # Handle specific currencies that might not use 100 as divisor? 
    # For now, standard division by 100.
    formatted_val = f"{final_price / 100:.2f}"
    
    return f"{formatted_val} {currency}"

if __name__ == "__main__":
    # Test search
    results = search_games("Age of Empires", "US")
    for item in results:
        name = item.get("name")
        price = item.get("price", {})
        print(f"Found: {name} (ID: {item.get('id')}) - Price: {format_price(price)}")
