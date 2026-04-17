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
        print(f"Location: Using STEAM_COUNTRY_CODE override from environment: {env_cc.upper()}")
        return env_cc.upper()

    # 2. Check for cache file
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                cached_cc = data.get("country_code")
                if cached_cc:
                    print(f"Location: Loaded cached region: {cached_cc.upper()}")
                    return cached_cc.upper()
        except (json.JSONDecodeError, IOError):
            pass 

    # 3. Live detection
    print("Location: Detecting region via GeoIP...")
    try:
        with httpx.Client(timeout=10.0) as client:
            # Get public IP using ipify (HTTPS)
            ip_resp = client.get("https://api.ipify.org?format=json")
            ip_resp.raise_for_status()
            public_ip = ip_resp.json().get("ip")

            if public_ip:
                country_code = None
                
                # Primary: ipapi.co (HTTPS)
                try:
                    geo_resp = client.get(f"https://ipapi.co/{public_ip}/json/")
                    if geo_resp.status_code == 200:
                        country_code = geo_resp.json().get("country_code")
                except Exception:
                    pass
                
                # Fallback: freeipapi.com (HTTPS)
                if not country_code:
                    try:
                        print("Location: Primary GeoIP rate-limited or failed. Trying fallback...")
                        geo_resp = client.get(f"https://freeipapi.com/api/json/{public_ip}")
                        if geo_resp.status_code == 200:
                            # freeipapi uses countryCode (2 letters)
                            country_code = geo_resp.json().get("countryCode")
                    except Exception:
                        pass

                if country_code and len(country_code) == 2:
                    country_code = country_code.upper()
                    print(f"Location: Detected region {country_code} for IP {public_ip[:7]}...")
                    # Save to cache
                    try:
                        with open(CACHE_FILE, "w") as f:
                            json.dump({"country_code": country_code}, f)
                    except IOError:
                        pass
                    return country_code
                else:
                    print("Location: All GeoIP services failed to detect region.")
    except Exception as e:
        # Log minimal error to avoid IP/service leakage
        print(f"Location Error: Detection failed ({str(e)[:50]})")
    
    # Default to US if detection fails
    return "US"

if __name__ == "__main__":
    print(f"Detected Country Code: {get_country_code()}")
