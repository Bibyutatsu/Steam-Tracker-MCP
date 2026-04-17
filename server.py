import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from steam_api import search_games, format_price, get_official_wishlist, get_player_summaries, get_apps_details_batch
from utils import get_country_code

# Load environment variables
load_dotenv()

STEAM_ID = os.getenv("STEAM_ID")

# Initialize FastMCP server
mcp = FastMCP("Steam Price Tracker", host="0.0.0.0")

# Detect location on startup
COUNTRY_CODE = get_country_code()

@mcp.tool()
async def get_game_prices(query: str) -> str:
    """
    Search for Steam games by name and return their current prices and details.
    """
    # Use the detected country code for local results
    results = search_games(query, country_code=COUNTRY_CODE)
    
    if not results:
        return f"No matching games found for '{query}' in region '{COUNTRY_CODE}'."
    
    response = []
    response.append(f"### Steam Search Results for '{query}' (Region: {COUNTRY_CODE}):\n")
    
    for item in results:
        name = item.get("name")
        appid = item.get("id")
        price_info = item.get("price")
        
        formatted_price = format_price(price_info)
        
        # Check if it's on sale
        discount_percent = 0
        if price_info:
            initial = price_info.get("initial", 0)
            final = price_info.get("final", 0)
            if initial > final:
                discount_percent = int(((initial - final) / initial) * 100)
        
        status = f"**{formatted_price}**"
        if discount_percent > 0:
            status += f" (~~{initial/100:.2f}~~ -{discount_percent}%)"
        
        store_url = f"https://store.steampowered.com/app/{appid}"
        
        response.append(f"- **{name}**")
        response.append(f"  - Price: {status}")
        response.append(f"  - App ID: `{appid}`")
        response.append(f"  - Store Link: [View on Steam]({store_url})")
        response.append("")
    
    return "\n".join(response)

@mcp.tool()
async def get_my_wishlist(sort_by_discount: bool = True) -> str:
    """
    Fetch your Steam wishlist using the official Web API and show current prices/deals.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured in .env."
    
    # 1. Get AppIDs from official Web API
    wishlist_items = get_official_wishlist(STEAM_ID)
    if not wishlist_items:
        return f"No wishlist items found for Steam ID {STEAM_ID} via official API. Check your privacy settings."
        
    appids = [item.get("appid") for item in wishlist_items]
    
    # 2. Get details in batches (Steam allows ~200 at once, but we'll do 50 to be safe)
    batch_size = 50
    all_details = {}
    for i in range(0, len(appids), batch_size):
        chunk = appids[i:i + batch_size]
        details = get_apps_details_batch(chunk, country_code=COUNTRY_CODE)
        all_details.update(details)
    
    # 3. Process and format
    items = []
    for appid_str, result in all_details.items():
        if not result.get("success"):
            continue
            
        data = result.get("data", {})
        price_overview = data.get("price_overview", {})
        
        items.append({
            "name": data.get("name", "Unknown"),
            "appid": appid_str,
            "price": price_overview.get("final", 0),
            "discount": price_overview.get("discount_percent", 0),
            "initial": price_overview.get("initial", 0),
            "currency": price_overview.get("currency", "")
        })
    
    # 4. Sort
    if sort_by_discount:
        items.sort(key=lambda x: x["discount"], reverse=True)
    else:
        items.sort(key=lambda x: x["price"])
        
    response = [f"### Your Steam Wishlist (Region: {COUNTRY_CODE}):\n"]
    for item in items:
        status = format_price({"final": item["price"], "currency": item["currency"]})
        if item["discount"] > 0:
            status = f"**{status}** (-{item['discount']}%)"
        
        line = f"- **[{item['name']}](https://store.steampowered.com/app/{item['appid']})**: {status}"
        response.append(line)
        
    return "\n".join(response)

@mcp.tool()
async def get_my_profile() -> str:
    """
    Get your basic Steam profile status and recently played information.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured in .env."
        
    players = get_player_summaries(STEAM_ID)
    if not players:
        return "Could not retrieve profile info."
        
    p = players[0]
    persona = p.get("personaname")
    status_code = p.get("personastate", 0)
    status_map = {0: "Offline", 1: "Online", 2: "Busy", 3: "Away", 4: "Snooze", 5: "Looking to Trade", 6: "Looking to Play"}
    status = status_map.get(status_code, "Unknown")
    
    game_info = ""
    if p.get("gameextrainfo"):
        game_info = f"\nCurrently playing: **{p.get('gameextrainfo')}**"
        
    response = f"### Steam Profile: {persona}\n- Status: **{status}**{game_info}\n- Profile Link: {p.get('profileurl')}"
    return response

if __name__ == "__main__":
    mcp.run()
