import requests
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

STEAM_WEB_API_KEY = os.getenv("STEAM_WEB_API_KEY")

async def get_and_cache_profile_image(steam_id, cache_filename="profile_avatar.png"):
    """
    Fetches the Steam profile image and caches it locally.
    Returns the absolute cache path on success, None on failure.
    Uses MOUNT_PATH from environment if available.
    """
    if not STEAM_WEB_API_KEY or not steam_id:
        return None
    
    mount_path = os.getenv("MOUNT_PATH", ".")
    cache_path = os.path.join(mount_path, cache_filename)
    
    # Ensure directory exists
    if mount_path != "." and not os.path.exists(mount_path):
        os.makedirs(mount_path, exist_ok=True)

    # Check if cache exists
    if os.path.exists(cache_path):
        return cache_path

    try:
        async with httpx.AsyncClient() as client:
            # Get Player Summaries
            url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_WEB_API_KEY}&steamids={steam_id}"
            response = await client.get(url)
            data = response.json()
            
            players = data.get("response", {}).get("players", [])
            if players:
                avatar_url = players[0].get("avatarfull")
                if avatar_url:
                    img_data = await client.get(avatar_url)
                    with open(cache_path, "wb") as f:
                        f.write(img_data.content)
                    return cache_path
    except Exception as e:
        print(f"Error fetching profile image: {e}")
    return None

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

def get_current_players(appid):
    """
    Fetches exact, real-time live player counts for any Steam AppID.
    """
    url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
    params = {"appid": appid}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        result = data.get("response", {}).get("result")
        if result == 1:
            return data.get("response", {}).get("player_count", 0)
        return None
    except Exception as e:
        print(f"Error fetching player count for {appid}: {e}")
        return None

def get_owned_games(steam_id):
    """
    Retrieves a user's entire library along with their exact playtime.
    Requires STEAM_WEB_API_KEY.
    """
    if not STEAM_WEB_API_KEY:
        print("STEAM_WEB_API_KEY not found.")
        return []

    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "steamid": steam_id,
        "include_appinfo": 1,
        "format": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("response", {}).get("games", [])
    except Exception as e:
        print(f"Error fetching owned games for {steam_id}: {e}")
        return []

def get_app_news(appid, count=3):
    """
    Fetches the latest patch notes, announcements, and developer news for a game.
    """
    url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
    params = {
        "appid": appid,
        "count": count,
        "maxlength": 1000,
        "format": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("appnews", {}).get("newsitems", [])
    except Exception as e:
        print(f"Error fetching news for {appid}: {e}")
        return []

def resolve_vanity_url(vanity_url):
    """
    Converts a custom profile URL name to a 64-bit Steam ID.
    """
    if not STEAM_WEB_API_KEY:
        print("STEAM_WEB_API_KEY not found.")
        return None
        
    url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "vanityurl": vanity_url
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("response", {}).get("success") == 1:
            return data.get("response", {}).get("steamid")
        return None
    except Exception as e:
        print(f"Error resolving vanity URL {vanity_url}: {e}")
        return None

def get_recently_played_games(steam_id, count=None):
    """
    Returns a list of games a player has played in the last two weeks.
    """
    if not STEAM_WEB_API_KEY:
        return []
    url = "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "steamid": steam_id,
        "format": "json"
    }
    if count:
        params["count"] = count
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("response", {}).get("games", [])
    except Exception as e:
        print(f"Error fetching recently played games: {e}")
        return []

def get_player_achievements(steam_id, appid, language="english"):
    """
    Returns a list of achievements a user has unlocked for a specific app.
    """
    if not STEAM_WEB_API_KEY:
        return None
    url = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "steamid": steam_id,
        "appid": appid,
        "l": language,
        "format": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("playerstats", {}).get("achievements", [])
    except Exception as e:
        print(f"Error fetching player achievements: {e}")
        return None

def get_global_achievement_percentages(appid):
    """
    Returns global completion percentages for achievements in a game.
    """
    url = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/"
    params = {
        "gameid": appid,
        "format": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("achievementpercentages", {}).get("achievements", [])
    except Exception as e:
        print(f"Error fetching global achievements: {e}")
        return []

def get_friend_list(steam_id, relationship="friend"):
    """
    Returns the friend list of a Steam user.
    """
    if not STEAM_WEB_API_KEY:
        return []
    url = "https://api.steampowered.com/ISteamUser/GetFriendList/v0001/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "steamid": steam_id,
        "relationship": relationship,
        "format": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("friendslist", {}).get("friends", [])
    except Exception as e:
        print(f"Error fetching friend list: {e}")
        return []

def get_featured_categories(language="english"):
    """
    Fetches the featured categories (Specials, Top Sellers, etc.) from the Steam Store Frontpage API.
    """
    url = "https://store.steampowered.com/api/featuredcategories/"
    params = {"l": language}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching featured categories: {e}")
        return {}

if __name__ == "__main__":
    # Test search
    results = search_games("Age of Empires", "US")
    for item in results:
        name = item.get("name")
        price = item.get("price", {})
        print(f"Found: {name} (ID: {item.get('id')}) - Price: {format_price(price)}")
