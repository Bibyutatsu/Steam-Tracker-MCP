import os
import json
import time
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

STEAM_WEB_API_KEY = os.getenv("STEAM_WEB_API_KEY")
MOUNT_PATH = os.getenv("MOUNT_PATH", ".")

def sanitize_url(url: str) -> str:
    """Removes sensitive keys from URLs for safe logging."""
    if not url: return url
    if STEAM_WEB_API_KEY and STEAM_WEB_API_KEY in url:
        return url.replace(STEAM_WEB_API_KEY, "[REDACTED_API_KEY]")
    return url

async def safe_get(client, url, params=None, timeout=10.0):
    """Performs a GET request and handles errors without leaking the API key."""
    try:
        response = await client.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as e:
        # Clean error message
        clean_url = sanitize_url(str(e.request.url))
        print(f"HTTP Error {e.response.status_code} for {clean_url}")
        return None
    except Exception as e:
        clean_msg = sanitize_url(str(e))
        print(f"Request Error: {clean_msg}")
        return None

class PriceCache:
    """
    Handles local persistence of game prices to avoid redundant API calls.
    """
    def __init__(self, ttl_seconds=86400): # Default 24 hours
        self.cache_file = os.path.join(MOUNT_PATH, ".price_cache.json")
        self.ttl = ttl_seconds
        self.data = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.data, f)
        except IOError as e:
            print(f"Error saving price cache: {e}")

    def get(self, appid, country_code):
        key = f"{appid}_{country_code}"
        entry = self.data.get(key)
        if entry:
            # Check TTL
            if time.time() - entry.get("timestamp", 0) < self.ttl:
                return entry.get("price_data")
        return None

    def set(self, appid, country_code, price_data):
        key = f"{appid}_{country_code}"
        self.data[key] = {
            "timestamp": time.time(),
            "price_data": price_data
        }

price_cache = PriceCache()

async def get_and_cache_profile_image(steam_id, cache_filename="profile_avatar.png"):
    """
    Fetches the Steam profile image and caches it locally.
    Uses MOUNT_PATH from environment if available.
    """
    # Basic SteamID validation (17 digits)
    if not steam_id or not str(steam_id).isdigit() or len(str(steam_id)) != 17:
        return None
        
    if not STEAM_WEB_API_KEY:
        return None
    
    cache_path = os.path.join(MOUNT_PATH, cache_filename)
    
    # Ensure directory exists
    if MOUNT_PATH != "." and not os.path.exists(MOUNT_PATH):
        os.makedirs(MOUNT_PATH, exist_ok=True)

    # Check if cache exists
    if os.path.exists(cache_path):
        return cache_path

    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
            params = {
                "key": STEAM_WEB_API_KEY,
                "steamids": steam_id
            }
            response = await safe_get(client, url, params=params)
            if not response: return None
            
            data = response.json()
            players = data.get("response", {}).get("players", [])
            if players:
                avatar_url = players[0].get("avatarfull")
                if avatar_url:
                    img_data = await client.get(avatar_url)
                    with open(cache_path, "wb") as f:
                        f.write(img_data.content)
                    return cache_path
    except Exception:
        pass
    return None

async def search_games(term, country_code="US", language="english"):
    """
    Searches the Steam store for games matching the term.
    """
    # Basic sanitization: limit length and check for weird characters
    term = str(term)[:100].strip()
    if not term: return []

    url = "https://store.steampowered.com/api/storesearch/"
    params = {
        "term": term,
        "l": language,
        "cc": country_code
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return []
            data = response.json()
            
            if data.get("total", 0) > 0:
                return data.get("items", [])
            return []
    except Exception:
        return []

async def get_app_details(appid, country_code="US", language="english"):
    """
    Retrieves detailed information (including precise pricing) for a specific app ID.
    Uses cache if available.
    """
    if not str(appid).isdigit():
        return None
        
    # Check cache first
    cached = price_cache.get(appid, country_code)
    if cached:
        return cached

    url = "https://store.steampowered.com/api/appdetails"
    params = {
        "appids": appid,
        "cc": country_code,
        "l": language,
        "filters": "price_overview,basic"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return None
            data = response.json()
            
            app_data = data.get(str(appid))
            if app_data and app_data.get("success"):
                res_data = app_data.get("data")
                # Save to cache
                price_cache.set(appid, country_code, res_data)
                price_cache.save_cache()
                return res_data
            return None
    except Exception:
        return None

async def get_apps_details_batch(appids, country_code="US", language="english"):
    """
    Retrieves pricing information for multiple app IDs in optimized batches of 100.
    """
    results = {}
    remaining_appids = []

    # 1. Check cache for all requested IDs
    for appid in appids:
        cached = price_cache.get(appid, country_code)
        if cached:
            results[str(appid)] = {"success": True, "data": cached}
        else:
            remaining_appids.append(appid)

    if not remaining_appids:
        return results

    # 2. Fetch remaining IDs in chunks of 50 (Steam allows 100, but 50 is more reliable)
    chunk_size = 50
    chunks = [remaining_appids[i:i + chunk_size] for i in range(0, len(remaining_appids), chunk_size)]

    async def fetch_chunk(chunk):
        ids_str = ",".join(map(str, chunk))
        url = "https://store.steampowered.com/api/appdetails"
        params = {
            "appids": ids_str,
            "cc": country_code,
            "l": language,
            "filters": "price_overview" # Mandatory for batching
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await safe_get(client, url, params=params, timeout=15.0)
                if response and response.status_code == 200:
                    return response.json() or {}
                return {}
        except Exception:
            return {}

    # Fetch all chunks in parallel (with some concurrency limit if needed, here we just gather)
    # Using small delay between chunks might help avoid 429
    chunk_responses = []
    for chunk in chunks:
        chunk_responses.append(fetch_chunk(chunk))
        await asyncio.sleep(0.5) # Gentle rate limiting

    all_responses = await asyncio.gather(*chunk_responses)

    # 3. Process responses and update cache
    updated_cache = False
    for resp in all_responses:
        if not resp: continue
        for appid_str, result in resp.items():
            if result.get("success"):
                data = result.get("data")
                # Handle the case where 'data' is empty list [] for free games
                if isinstance(data, list) and not data:
                    data = {"price_overview": {"final": 0, "initial": 0, "discount_percent": 0, "currency": ""}}
                
                results[appid_str] = {"success": True, "data": data}
                price_cache.set(appid_str, country_code, data)
                updated_cache = True
            else:
                results[appid_str] = {"success": False, "data": None}

    if updated_cache:
        price_cache.save_cache()

    return results

async def get_official_wishlist(steam_id):
    """
    Retrieves the wishlist AppIDs for a given Steam ID using the official IWishlistService.
    """
    if not steam_id or not str(steam_id).isdigit():
        return []
        
    if not STEAM_WEB_API_KEY:
        return []
        
    url = "https://api.steampowered.com/IWishlistService/GetWishlist/v1/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "steamid": steam_id
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params, timeout=15.0)
            if not response: return []
            data = response.json()
            return data.get("response", {}).get("items", [])
    except Exception:
        return []

async def get_player_summaries(steam_ids):
    """
    Fetches basic profile information for a list of Steam IDs.
    """
    # steam_ids can be a comma separated string, validate it minimally
    if not steam_ids or not all(part.strip().isdigit() for part in str(steam_ids).split(",")):
        return []

    if not STEAM_WEB_API_KEY:
        return []
        
    url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "steamids": steam_ids
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return []
            data = response.json()
            return data.get("response", {}).get("players", [])
    except Exception:
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

async def get_current_players(appid):
    """
    Fetches exact, real-time live player counts for any Steam AppID.
    """
    if not str(appid).isdigit():
        return None

    url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
    params = {"appid": appid}
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return None
            data = response.json()
            result = data.get("response", {}).get("result")
            if result == 1:
                return data.get("response", {}).get("player_count", 0)
            return None
    except Exception:
        return None

async def get_owned_games(steam_id):
    """
    Retrieves a user's entire library along with their exact playtime.
    """
    if not steam_id or not str(steam_id).isdigit():
        return []

    if not STEAM_WEB_API_KEY:
        return []

    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "steamid": steam_id,
        "include_appinfo": 1,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params, timeout=20.0)
            if not response: return []
            data = response.json()
            return data.get("response", {}).get("games", [])
    except Exception:
        return []

async def get_app_news(appid, count=3):
    """
    Fetches the latest patch notes, announcements, and developer news for a game.
    """
    if not str(appid).isdigit():
        return []

    url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
    params = {
        "appid": appid,
        "count": count,
        "maxlength": 1000,
        "format": "json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return []
            data = response.json()
            return data.get("appnews", {}).get("newsitems", [])
    except Exception:
        return []

async def resolve_vanity_url(vanity_url):
    """
    Converts a custom profile URL name to a 64-bit Steam ID.
    """
    vanity_url = str(vanity_url).strip()
    if not vanity_url: return None

    if not STEAM_WEB_API_KEY:
        return None
        
    url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"
    params = {
        "key": STEAM_WEB_API_KEY,
        "vanityurl": vanity_url
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return None
            data = response.json()
            if data.get("response", {}).get("success") == 1:
                return data.get("response", {}).get("steamid")
            return None
    except Exception:
        return None

async def get_recently_played_games(steam_id, count=None):
    """
    Returns a list of games a player has played in the last two weeks.
    """
    if not steam_id or not str(steam_id).isdigit():
        return []

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
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return []
            data = response.json()
            return data.get("response", {}).get("games", [])
    except Exception:
        return []

async def get_player_achievements(steam_id, appid, language="english"):
    """
    Returns a list of achievements a user has unlocked for a specific app.
    """
    if not steam_id or not str(steam_id).isdigit():
        return None
    if not str(appid).isdigit():
        return None

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
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return None
            data = response.json()
            return data.get("playerstats", {}).get("achievements", [])
    except Exception:
        return None

async def get_global_achievement_percentages(appid):
    """
    Returns global completion percentages for achievements in a game.
    """
    if not str(appid).isdigit():
        return []

    url = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/"
    params = {
        "gameid": appid,
        "format": "json"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return []
            data = response.json()
            return data.get("achievementpercentages", {}).get("achievements", [])
    except Exception:
        return []

async def get_friend_list(steam_id, relationship="friend"):
    """
    Returns the friend list of a Steam user.
    """
    if not steam_id or not str(steam_id).isdigit():
        return []

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
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return []
            data = response.json()
            return data.get("friendslist", {}).get("friends", [])
    except Exception:
        return []

async def get_featured_categories(language="english"):
    """
    Fetches the featured categories (Specials, Top Sellers, etc.) from the Steam Store Frontpage API.
    """
    url = "https://store.steampowered.com/api/featuredcategories/"
    params = {"l": language}
    try:
        async with httpx.AsyncClient() as client:
            response = await safe_get(client, url, params=params)
            if not response: return {}
            return response.json()
    except Exception:
        return {}
