import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Persistence Path Management
MOUNT_PATH = os.getenv("MOUNT_PATH", ".")
CACHE_FILE = os.path.join(MOUNT_PATH, ".location_cache")

# Ensure the mount path exists if it's specified
if MOUNT_PATH != "." and not os.path.exists(MOUNT_PATH):
    try:
        os.makedirs(MOUNT_PATH, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create MOUNT_PATH {MOUNT_PATH}: {e}")


def get_country_code():
    """
    Detects the country code of the current user.
    Priority:
    1. STEAM_COUNTRY_CODE in .env
    2. Cached value in .location_cache file
    3. Live detection via GeoIP API (and save to cache)
    """
    # 1. Check for override in .env
    env_cc = os.getenv("STEAM_COUNTRY_CODE")
    if env_cc:
        return env_cc.upper()

    # 2. Check for cache file
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                cached_cc = data.get("country_code")
                if cached_cc:
                    return cached_cc.upper()
        except (json.JSONDecodeError, IOError):
            pass 

    # 3. Live detection
    try:
        with httpx.Client(timeout=10.0) as client:
            # Get public IP using ipify
            ip_resp = client.get("https://api.ipify.org?format=json")
            ip_resp.raise_for_status()
            public_ip = ip_resp.json().get("ip")

            if public_ip:
                # Get country code using ip-api
                geo_resp = client.get(f"http://ip-api.com/json/{public_ip}")
                geo_resp.raise_for_status()
                country_code = geo_resp.json().get("countryCode")
                
                if country_code:
                    country_code = country_code.upper()
                    # Save to cache
                    try:
                        with open(CACHE_FILE, "w") as f:
                            json.dump({"country_code": country_code}, f)
                    except IOError:
                        pass
                    return country_code
    except Exception as e:
        print(f"Error detecting location: {e}")
    
    # Default to US if detection fails
    return "US"

if __name__ == "__main__":
    print(f"Detected Country Code: {get_country_code()}")
