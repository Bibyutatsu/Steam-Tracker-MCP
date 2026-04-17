import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from steam_api import (
    search_games, format_price, get_official_wishlist, 
    get_player_summaries, get_apps_details_batch,
    get_current_players, get_owned_games, get_app_news, resolve_vanity_url,
    get_recently_played_games, get_player_achievements,
    get_global_achievement_percentages, get_friend_list, get_featured_categories
)
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
    Get your own basic Steam profile status and recently played information.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured in .env."
        
    return await get_player_info(STEAM_ID)

@mcp.tool()
async def get_live_player_count(appid: int) -> str:
    """
    Get the number of players currently playing a game on Steam.
    """
    count = get_current_players(appid)
    if count is None:
        return f"Could not retrieve player count for AppID {appid}."
    return f"There are currently **{count:,}** players in-game for AppID `{appid}`."

@mcp.tool()
async def get_game_news(appid: int, count: int = 3) -> str:
    """
    Get the latest news and patch notes for a specific Steam game.
    """
    news_items = get_app_news(appid, count)
    if not news_items:
        return f"No news found for AppID {appid}."
    
    response = [f"### Latest News for AppID {appid}:\n"]
    for item in news_items:
        title = item.get("title", "No Title")
        url = item.get("url", "#")
        author = item.get("author", "Unknown")
        # Strip some HTML if present, though Steam usually gives BBCode or clean text
        content = item.get("contents", "")[:500] + "..."
        response.append(f"#### [{title}]({url})")
        response.append(f"By: {author}")
        response.append(f"{content}\n")
    
    return "\n".join(response)

@mcp.tool()
async def analyze_my_library(sort_by: str = "playtime", limit: int = 15) -> str:
    """
    Analyze your Steam library. 
    sort_by can be 'playtime' (total hours) or 'name'.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured in .env."
        
    games = get_owned_games(STEAM_ID)
    if not games:
        return "Could not retrieve your library. Ensure your profile is public or your API key is correct."
        
    # Process games
    processed_games = []
    for g in games:
        processed_games.append({
            "name": g.get("name", "Unknown"),
            "playtime_hours": round(g.get("playtime_forever", 0) / 60, 1),
            "appid": g.get("appid")
        })
        
    if sort_by == "playtime":
        processed_games.sort(key=lambda x: x["playtime_hours"], reverse=True)
    else:
        processed_games.sort(key=lambda x: x["name"])
        
    display_games = processed_games[:limit]
    
    response = [f"### Your Steam Library Analysis (Top {len(display_games)} by {sort_by}):\n"]
    response.append(f"Total games owned: **{len(processed_games)}**\n")
    
    for g in display_games:
        response.append(f"- **{g['name']}**: {g['playtime_hours']} hours (AppID: `{g['appid']}`)")
        
    return "\n".join(response)

@mcp.tool()
async def resolve_steam_user(vanity_name: str) -> str:
    """
    Resolve a Steam vanity URL name (e.g. 'gabelogannewell') to a 64-bit SteamID.
    """
    steamid = resolve_vanity_url(vanity_name)
    if not steamid:
        return f"Could not resolve vanity name '{vanity_name}' to a SteamID."
    return f"The SteamID for '{vanity_name}' is: `{steamid}`"

@mcp.tool()
async def get_player_info(steam_id: str) -> str:
    """
    Get generic profile information for any public SteamID.
    """
    players = get_player_summaries(steam_id)
    if not players:
        return f"Could not retrieve profile info for SteamID {steam_id}."
        
    p = players[0]
    persona = p.get("personaname")
    status_code = p.get("personastate", 0)
    status_map = {0: "Offline", 1: "Online", 2: "Busy", 3: "Away", 4: "Snooze", 5: "Looking to Trade", 6: "Looking to Play"}
    status = status_map.get(status_code, "Unknown")
    
    game_info = ""
    if p.get("gameextrainfo"):
        game_info = f"\nCurrently playing: **{p.get('gameextrainfo')}**"
        
    return f"### Steam Profile: {persona}\n- SteamID: `{steam_id}`\n- Status: **{status}**{game_info}\n- Profile Link: {p.get('profileurl')}"

@mcp.tool()
async def get_recent_activity(steam_id: str = None) -> str:
    """
    Get games played in the last 2 weeks for a SteamID (defaults to yours).
    """
    target_id = steam_id or STEAM_ID
    if not target_id:
        return "No SteamID provided and STEAM_ID not configured."
        
    games = get_recently_played_games(target_id)
    if not games:
        return f"No recent activity found for SteamID {target_id} (or profile is private)."
        
    response = [f"### Recent Activity (Last 2 Weeks) for `{target_id}`:\n"]
    for g in games:
        hours = round(g.get("playtime_2weeks", 0) / 60, 1)
        total = round(g.get("playtime_forever", 0) / 60, 1)
        response.append(f"- **{g.get('name')}**: {hours} hrs recently ({total} hrs total)")
        
    return "\n".join(response)

@mcp.tool()
async def get_friends(steam_id: str = None) -> str:
    """
    Get the friend list for a SteamID (defaults to yours).
    """
    target_id = steam_id or STEAM_ID
    if not target_id:
        return "No SteamID provided and STEAM_ID not configured."
        
    friends = get_friend_list(target_id)
    if not friends:
        return f"Could not retrieve friends for `{target_id}` (profile/friend list is private)."
        
    # Get summaries for these friends to show names
    friend_ids = ",".join([f["steamid"] for f in friends[:50]]) # Limit to 50 for summary
    summaries = get_player_summaries(friend_ids)
    
    response = [f"### Friend List for `{target_id}` ({len(friends)} friends):\n"]
    for p in summaries:
        status_code = p.get("personastate", 0)
        status_map = {0: "Offline", 1: "Online", 2: "Busy", 3: "Away", 4: "Snooze", 5: "Looking to Trade", 6: "Looking to Play"}
        status = status_map.get(status_code, "Unknown")
        game = f" (Playing: {p.get('gameextrainfo')})" if p.get("gameextrainfo") else ""
        response.append(f"- **{p.get('personaname')}**: {status}{game}")
        
    return "\n".join(response)

@mcp.tool()
async def get_achievement_stats(appid: int, steam_id: str = None) -> str:
    """
    Compare your achievements with global rarity for a specific game.
    """
    target_id = steam_id or STEAM_ID
    if not target_id:
        return "No SteamID provided and STEAM_ID not configured."
        
    # 1. Get player achievements
    player_ach = get_player_achievements(target_id, appid)
    if player_ach is None:
        return f"Could not retrieve achievements for AppID {appid} (profile/game data private)."
        
    # 2. Get global percentages
    global_ach = get_global_achievement_percentages(appid)
    global_map = {a["name"]: a["percent"] for a in global_ach}
    
    # 3. Combine
    response = [f"### Achievement Stats for AppID `{appid}`:\n"]
    unlocked = [a for a in player_ach if a.get("achieved") == 1]
    response.append(f"You have unlocked **{len(unlocked)}/{len(player_ach)}** achievements.\n")
    
    # Show some rare ones or recent ones
    response.append("#### Rare Achievements You've Earned:")
    earned_with_rarity = []
    for a in unlocked:
        rarity = global_map.get(a["apiname"], 100)
        earned_with_rarity.append((a.get("name") or a["apiname"], rarity))
    
    earned_with_rarity.sort(key=lambda x: x[1])
    for name, rarity in earned_with_rarity[:5]:
        response.append(f"- **{name}**: {rarity:.1f}% of players have this")
        
    return "\n".join(response)

@mcp.tool()
async def get_top_specials() -> str:
    """
    Get the top featured "Specials" (deals) from the Steam homepage.
    """
    featured = get_featured_categories()
    specials = featured.get("specials", {}).get("items", [])
    
    if not specials:
        return "Could not find any featured specials right now."
        
    response = ["### Current Featured Specials on Steam:\n"]
    for item in specials:
        name = item.get("name")
        discount = item.get("discount_percent")
        # Format prices (they are in subunits)
        final = item.get("final_price", 0) / 100
        original = item.get("original_price", 0) / 100
        currency = item.get("currency", "")
        
        response.append(f"- **{name}**: {final:.2f} {currency} (-{discount}%) [~~{original:.2f}~~]")
        
    return "\n".join(response)


if __name__ == "__main__":
    mcp.run()
