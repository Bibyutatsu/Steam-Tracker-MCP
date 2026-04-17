import os
import json
import time
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

STEAM_WEB_API_KEY = os.getenv("STEAM_WEB_API_KEY")
ITAD_API_KEY = os.getenv("ITAD_API_KEY")
MOUNT_PATH = os.getenv("MOUNT_PATH", ".")
if MOUNT_PATH != "." and not os.path.exists(MOUNT_PATH):
    try:
        os.makedirs(MOUNT_PATH, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create MOUNT_PATH {MOUNT_PATH}: {e}")

def sanitize_url(url: str) -> str:
    """Removes sensitive keys from URLs for safe logging."""
    if not url: return url
    if STEAM_WEB_API_KEY and STEAM_WEB_API_KEY in url:
        return url.replace(STEAM_WEB_API_KEY, "[REDACTED_STEAM_KEY]")
    if ITAD_API_KEY and ITAD_API_KEY in url:
        return url.replace(ITAD_API_KEY, "[REDACTED_ITAD_KEY]")
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

async def get_app_names_batch(appids):
    """
    Fetches game names for a list of AppIDs using ICommunityService/GetApps.
    """
    if not appids:
        return {}
    
    if not STEAM_WEB_API_KEY:
        return {}
        
    url = "https://api.steampowered.com/ICommunityService/GetApps/v1/"
    
    # Process in chunks of 50 (safer for URL length)
    chunk_size = 50
    all_names = {}
    
    for i in range(0, len(appids), chunk_size):
        chunk = appids[i:i + chunk_size]
        params = {"key": STEAM_WEB_API_KEY}
        for j, appid in enumerate(chunk):
            params[f"appids[{j}]"] = appid
            
        try:
            async with httpx.AsyncClient() as client:
                response = await safe_get(client, url, params=params)
                if response:
                    data = response.json()
                    apps = data.get("response", {}).get("apps", [])
                    for app in apps:
                        all_names[str(app.get("appid"))] = app.get("name")
        except Exception:
            pass
            
    return all_names

async def resolve_app_details_batch(appids, country_code="US", language="english"):
    """
    Unified resolver that fetches BOTH metadata and pricing for a list of AppIDs.
    Uses ICommunityService/GetApps for names and Store API for prices.
    """
    results = {}
    remaining_appids = []

    # 1. Check cache and identify what's truly missing
    for appid in appids:
        appid_str = str(appid)
        cached = price_cache.get(appid_str, country_code)
        
        # We only count it as "cached" if it has both price and name
        if cached and cached.get("name") and cached.get("name") != "Unknown App":
            results[appid_str] = {"success": True, "data": cached}
        else:
            remaining_appids.append(int(appid))

    if not remaining_appids:
        return results

    # 2. Fetch missing data in parallel
    if remaining_appids:
        # Fetch names via Community API (High performance batch)
        name_task = get_app_names_batch(remaining_appids)
        
        # Fetch prices via Store API (Chunks of 50)
        chunk_size = 50
        chunks = [remaining_appids[i:i + chunk_size] for i in range(0, len(remaining_appids), chunk_size)]
        
        async def fetch_price_chunk(chunk):
            ids_str = ",".join(map(str, chunk))
            url = "https://store.steampowered.com/api/appdetails"
            params = {
                "appids": ids_str,
                "cc": country_code,
                "l": language,
                "filters": "price_overview"
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await safe_get(client, url, params=params, timeout=20.0)
                    return response.json() if response else {}
            except Exception: return {}

        price_tasks = [fetch_price_chunk(c) for c in chunks]
        
        # Execute all
        name_results = await asyncio.gather(name_task, *price_tasks)
        name_map = name_results[0]
        price_responses = name_results[1:]
        
        # 3. Merge and cache
        updated_cache = False
        for resp in price_responses:
            if not resp: continue
            for appid_str, result in resp.items():
                if result.get("success"):
                    data = result.get("data")
                    if isinstance(data, list) and not data: # Free games
                        data = {"price_overview": {"final": 0, "initial": 0, "discount_percent": 0, "currency": ""}}
                    
                    # Attach name from map OR fallout to existing cache name if we have it
                    resolved_name = name_map.get(appid_str)
                    if not resolved_name:
                        # Fallback: check if we ALREADY have a name in the cache that isn't Unknown
                        old_cached = price_cache.get(appid_str, country_code)
                        if old_cached and old_cached.get("name") and old_cached.get("name") != "Unknown App":
                            resolved_name = old_cached["name"]
                        else:
                            resolved_name = "Unknown App"

                    data["name"] = resolved_name
                    
                    results[appid_str] = {"success": True, "data": data}
                    price_cache.set(appid_str, country_code, data)
                    updated_cache = True
                else:
                    results[appid_str] = {"success": False, "data": None}

        if updated_cache:
            price_cache.save_cache()

    return results

async def get_wishlist_comprehensive(steam_id, country_code="US"):
    """
    Retrieves the entire wishlist with full metadata (name, price, discount).
    Combines the official ID fetcher with our high-performance batch resolver.
    """
    # 1. Get IDs using the proven simple API
    wishlist_items = await get_official_wishlist(steam_id)
    if not wishlist_items:
        return []
        
    appids = [item.get("appid") for item in wishlist_items]
    
    # 2. Resolve all details (names/prices) in one batch
    details = await resolve_app_details_batch(appids, country_code=country_code)
    
    processed = []
    for item in wishlist_items:
        appid_str = str(item.get("appid"))
        res = details.get(appid_str, {})
        if not res.get("success"):
            continue
            
        data = res.get("data", {})
        price_info = data.get("price_overview", {})
        
        processed.append({
            "appid": appid_str,
            "name": data.get("name", "Unknown"),
            "price": price_info.get("final", 0),
            "discount": price_info.get("discount_percent", 0),
            "currency": price_info.get("currency", ""),
            "is_on_sale": price_info.get("discount_percent", 0) > 0
        })
    
    return processed

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

async def get_library_audit(steam_id, country_code="US"):
    """
    Performs a deep audit of the user's library, combining playtime statistics
    with current market valuation and savings analysis.
    """
    games = await get_owned_games(steam_id)
    if not games: return None

    appids = [g["appid"] for g in games]
    details = await resolve_app_details_batch(appids, country_code=country_code)

    audit = {
        "total_games": len(games),
        "total_playtime_hrs": 0,
        "total_current_value": 0,
        "total_initial_value": 0,
        "never_played_count": 0,
        "currency": "",
        "top_played": [],
        "pile_of_shame": []
    }

    processed_games = []
    for g in games:
        appid = str(g["appid"])
        playtime = g.get("playtime_forever", 0) / 60
        audit["total_playtime_hrs"] += playtime
        
        if playtime == 0:
            audit["never_played_count"] += 1
            
        game_details = details.get(appid, {}).get("data") or {}
        price_info = game_details.get("price_overview", {})
        
        curr_price = price_info.get("final", 0)
        init_price = price_info.get("initial", curr_price)
        
        audit["total_current_value"] += curr_price
        audit["total_initial_value"] += init_price
        if not audit["currency"]: audit["currency"] = price_info.get("currency", "")

        processed_games.append({
            "name": game_details.get("name", g.get("name", "Unknown")),
            "playtime": round(playtime, 1),
            "appid": appid
        })

    # Sort and slice
    processed_games.sort(key=lambda x: x["playtime"], reverse=True)
    audit["top_played"] = processed_games[:10]
    
    return audit

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

class ITADClient:
    """
    Client for the IsThereAnyDeal (ITAD) API.
    Handles ID lookup, price history, and historical lows.
    """
    BASE_URL = "https://api.isthereanydeal.com"

    def __init__(self, api_key):
        self.api_key = api_key
        self.map_file = os.path.join(MOUNT_PATH, ".itad_map.json")
        self.mapping = self._load_mapping()

    def _load_mapping(self):
        if os.path.exists(self.map_file):
            try:
                with open(self.map_file, "r") as f:
                    return json.load(f)
            except: return {}
        return {}

    def _save_mapping(self):
        try:
            with open(self.map_file, "w") as f:
                json.dump(self.mapping, f)
        except: pass

    async def get_id(self, appid):
        """Maps Steam AppID to ITAD UUID."""
        appid_str = str(appid)
        if appid_str in self.mapping:
            return self.mapping[appid_str]

        if not self.api_key: return None

        url = f"{self.BASE_URL}/games/lookup/v1"
        params = {"appid": appid, "key": self.api_key}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await safe_get(client, url, params=params)
                if response:
                    data = response.json()
                    if data.get("found"):
                        itad_id = data["game"]["id"]
                        self.mapping[appid_str] = itad_id
                        self._save_mapping()
                        return itad_id
        except: pass
        return None

    async def get_history(self, appid, country="US"):
        """Fetches price history timeline for a game."""
        itad_id = await self.get_id(appid)
        if not itad_id or not self.api_key: return []

        url = f"{self.BASE_URL}/games/history/v2"
        # ITAD expects ISO format for 'since' without microseconds
        import datetime
        since_iso = (datetime.datetime.now() - datetime.timedelta(days=365)).replace(microsecond=0).isoformat() + "Z"

        params = {
            "id": itad_id,
            "country": country,
            "key": self.api_key,
            "since": since_iso
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await safe_get(client, url, params=params)
                if response:
                    return response.json()
        except: pass
        return []

    async def get_overview(self, appid, country="US"):
        """Fetches current prices and historical low summary using POST /overview/v2."""
        itad_id = await self.get_id(appid)
        if not itad_id or not self.api_key: return None

        url = f"{self.BASE_URL}/games/overview/v2"
        params = {"country": country, "key": self.api_key}
        # Based on docs, overview/v2 often requires POST with gids array
        payload = [itad_id] # Try as simple array of IDs
        
        try:
            async with httpx.AsyncClient() as client:
                # Some docs say POST with {"gids": [...]}, others just [...] 
                # Let's try JSON array first as that's common for v2
                response = await client.post(url, params=params, json=payload, timeout=10.0)
                if response.status_code == 405:
                    # Fallback to GET if POST is not the one
                    response = await client.get(url, params={"id": itad_id, "country": country, "key": self.api_key})
                
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"ITAD Overview Error: {e}")
        return None

itad_client = ITADClient(ITAD_API_KEY)
