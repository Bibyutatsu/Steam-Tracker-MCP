import os
import asyncio
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from steam_api import (
    search_games, format_price, get_wishlist_comprehensive, 
    get_player_summaries, resolve_app_details_batch,
    get_current_players, get_owned_games, get_app_news, resolve_vanity_url,
    get_recently_played_games, get_player_achievements,
    get_global_achievement_percentages, get_friend_list, get_featured_categories,
    get_library_audit
)
from utils import get_country_code

# Load environment variables
load_dotenv()

STEAM_ID = os.getenv("STEAM_ID")

# Initialize FastMCP server
mcp = FastMCP("Steam Price Tracker", host="0.0.0.0")

# Detect location on startup
COUNTRY_CODE = get_country_code()
print(f"### Steam Intelligence initialized in Region: {COUNTRY_CODE}")

# --- CATEGORY 1: PUBLIC STORE INTELLIGENCE ---

@mcp.tool()
async def get_game_prices(query: str) -> str:
    """
    Search for Steam games by name and return their current prices and details.
    """
    results = await search_games(query, country_code=COUNTRY_CODE)
    
    if not results:
        return f"No matching games found for '{query}' in region '{COUNTRY_CODE}'."
    
    response = []
    response.append(f"### Steam Search Results for '{query}' (Region: {COUNTRY_CODE}):\n")
    
    for item in results:
        name = item.get("name")
        appid = item.get("id")
        price_info = item.get("price")
        
        formatted_price = format_price(price_info)
        
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
async def get_bulk_prices(queries: list[str]) -> str:
    """
    Get current prices and deals for a list of game names or AppIDs.
    Example: queries=["Elden Ring", "730", "Cyberpunk 2077"]
    """
    # 1. Resolve queries to AppIDs
    async def resolve_one(q):
        if q.isdigit():
            return int(q), q
        results = await search_games(q, country_code=COUNTRY_CODE)
        if results:
            return results[0]["id"], results[0]["name"]
        return None, q

    resolutions = await asyncio.gather(*[resolve_one(q) for q in queries])
    
    appids_to_fetch = [r[0] for r in resolutions if r[0]]
    names_map = {str(r[0]): r[1] for r in resolutions if r[0]}
    
    if not appids_to_fetch:
        return "Could not resolve any of the provided queries."

    # 2. Fetch prices in batch using unified resolver
    prices_data = await resolve_app_details_batch(appids_to_fetch, country_code=COUNTRY_CODE)
    
    response = [f"### 🏷️ Bulk Price Results ({COUNTRY_CODE}):\n"]
    
    for appid_str, result in prices_data.items():
        name = names_map.get(appid_str, f"AppID {appid_str}")
        if not result.get("success"):
            response.append(f"- **{name}**: Data not available.")
            continue
            
        data = result.get("data", {})
        price_overview = data.get("price_overview", {})
        
        formatted = format_price(price_overview)
        discount = price_overview.get("discount_percent", 0)
        status = f"**{formatted}**"
        if discount > 0:
            status += f" (-{discount}%)"
            
        response.append(f"- **{name}** ([Store](https://store.steampowered.com/app/{appid_str})): {status}")
        
    return "\n".join(response)

@mcp.tool()
async def get_live_player_count(appid: int) -> str:
    """
    Get the number of players currently playing a game on Steam.
    """
    count = await get_current_players(appid)
    if count is None:
        return f"Could not retrieve player count for AppID {appid}."
    return f"There are currently **{count:,}** players in-game for AppID `{appid}`."

@mcp.tool()
async def get_game_news(appid: int, count: int = 3) -> str:
    """
    Get the latest news and patch notes for a specific Steam game.
    """
    news_items = await get_app_news(appid, count)
    if not news_items:
        return f"No news found for AppID {appid}."
    
    response = [f"### Latest News for AppID {appid}:\n"]
    for item in news_items:
        title = item.get("title", "No Title")
        url = item.get("url", "#")
        author = item.get("author", "Unknown")
        content = item.get("contents", "")[:500] + "..."
        response.append(f"#### [{title}]({url})")
        response.append(f"By: {author}")
        response.append(f"{content}\n")
    
    return "\n".join(response)

@mcp.tool()
async def get_top_specials() -> str:
    """
    Get the top featured "Specials" (deals) from the Steam homepage.
    """
    featured = await get_featured_categories()
    specials = featured.get("specials", {}).get("items", [])
    
    if not specials:
        return "Could not find any featured specials right now."
        
    response = ["### Current Featured Specials on Steam:\n"]
    for item in specials:
        name = item.get("name")
        discount = item.get("discount_percent")
        final = item.get("final_price", 0) / 100
        original = item.get("original_price", 0) / 100
        currency = item.get("currency", "")
        
        response.append(f"- **{name}**: {final:.2f} {currency} (-{discount}%) [~~{original:.2f}~~]")
        
    return "\n".join(response)

# --- CATEGORY 2: USER ACCOUNT INTELLIGENCE ---

@mcp.tool()
async def get_my_wishlist() -> str:
    """
    Fetch your Steam wishlist using the modern Service API with comprehensive metadata.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured in .env."
    
    items = await get_wishlist_comprehensive(STEAM_ID, country_code=COUNTRY_CODE)
    if not items:
        return f"No wishlist items found or profile is private for Steam ID {STEAM_ID}."
        
    response = [f"### Your Steam Wishlist ({COUNTRY_CODE}):\n"]
    for item in items:
        status = f"{item['price']/100:.2f} {item['currency']}"
        if item["discount"] > 0:
            status = f"**{status}** (-{item['discount']}%)"
        
        line = f"- **[{item['name']}](https://store.steampowered.com/app/{item['appid']})**: {status}"
        response.append(line)
        
    return "\n".join(response)

@mcp.tool()
async def audit_library() -> str:
    """
    Perform a complete audit of your Steam library, including value, playtime, and analytics.
    Replaces separate valuation and analysis tools.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured in .env."

    audit = await get_library_audit(STEAM_ID, country_code=COUNTRY_CODE)
    if not audit:
        return "Could not retrieve library. Ensure your profile is public or your API key is correct."

    account_value_curr = audit["total_current_value"] / 100
    account_value_init = audit["total_initial_value"] / 100
    pile_of_shame_pct = round((audit["never_played_count"] / audit["total_games"]) * 100, 1)
    
    avg_per_hour = 0
    if audit["total_playtime_hrs"] > 0:
        avg_per_hour = account_value_curr / audit["total_playtime_hrs"]

    response = [
        f"## 📊 Steam Library Audit: `{STEAM_ID}`",
        f"**Region**: {COUNTRY_CODE}\n",
        f"### 💰 Financial Breakdown",
        f"- **Total Current Value**: **{account_value_curr:.2f} {audit['currency']}** (at today's prices)",
        f"- **Total Original Value**: **{account_value_init:.2f} {audit['currency']}** (if bought full price)",
        f"- **Approx. Savings**: {(account_value_init - account_value_curr):.2f} {audit['currency']}\n",
        f"### 🎮 Gameplay Statistics",
        f"- **Total Games Owned**: **{audit['total_games']}**",
        f"- **Total Time Playing**: **{audit['total_playtime_hrs']:.1f} hours**",
        f"- **Pile of Shame**: **{audit['never_played_count']} games** ({pile_of_shame_pct}% never played)",
        f"- **Avg. Cost per Hour**: **{avg_per_hour:.2f} {audit['currency']}/hr**\n",
        f"### 🏆 Top 10 Most Played Games",
    ]
    
    for g in audit["top_played"]:
        response.append(f"- **{g['name']}**: {g['playtime']} hours")
        
    return "\n".join(response)

    if not appids_to_fetch:
        return "Could not resolve any of the provided queries."

    # 2. Fetch prices in batch using unified resolver
    prices_data = await resolve_app_details_batch(appids_to_fetch, country_code=COUNTRY_CODE)
    
    response = [f"### 🏷️ Bulk Price Results ({COUNTRY_CODE}):\n"]
    
    for appid_str, result in prices_data.items():
        name = names_map.get(appid_str, f"AppID {appid_str}")
        if not result.get("success"):
            response.append(f"- **{name}**: Data not available.")
            continue
            
        data = result.get("data", {})
        price_overview = data.get("price_overview", {})
        
        formatted = format_price(price_overview)
        discount = price_overview.get("discount_percent", 0)
        status = f"**{formatted}**"
        if discount > 0:
            status += f" (-{discount}%)"
            
        response.append(f"- **{name}** ([Store](https://store.steampowered.com/app/{appid_str})): {status}")
        
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
    count = await get_current_players(appid)
    if count is None:
        return f"Could not retrieve player count for AppID {appid}."
    return f"There are currently **{count:,}** players in-game for AppID `{appid}`."

@mcp.tool()
async def get_game_news(appid: int, count: int = 3) -> str:
    """
    Get the latest news and patch notes for a specific Steam game.
    """
    news_items = await get_app_news(appid, count)
    if not news_items:
        return f"No news found for AppID {appid}."
    
    response = [f"### Latest News for AppID {appid}:\n"]
    for item in news_items:
        title = item.get("title", "No Title")
        url = item.get("url", "#")
        author = item.get("author", "Unknown")
        content = item.get("contents", "")[:500] + "..."
        response.append(f"#### [{title}]({url})")
        response.append(f"By: {author}")
        response.append(f"{content}\n")
    
    return "\n".join(response)

# --- CATEGORY 3: EXTERNAL PROFILE UTILITIES ---

@mcp.tool()
async def resolve_steam_user(vanity_name: str) -> str:
    """
    Resolve a Steam vanity URL name (e.g. 'gabelogannewell') to a 64-bit SteamID.
    """
    steamid = await resolve_vanity_url(vanity_name)
    if not steamid:
        return f"Could not resolve vanity name '{vanity_name}' to a SteamID."
    return f"The SteamID for '{vanity_name}' is: `{steamid}`"

@mcp.tool()
async def get_player_info(steam_id: str) -> str:
    """
    Get generic profile information for any public SteamID.
    """
    players = await get_player_summaries(steam_id)
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
        
    games = await get_recently_played_games(target_id)
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
        
    friends = await get_friend_list(target_id)
    if not friends:
        return f"Could not retrieve friends for `{target_id}` (profile/friend list is private)."
        
    friend_ids = ",".join([f["steamid"] for f in friends[:50]]) 
    summaries = await get_player_summaries(friend_ids)
    
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
        
    player_ach = await get_player_achievements(target_id, appid)
    if player_ach is None:
        return f"Could not retrieve achievements for AppID {appid} (profile/game data private)."
        
    global_ach = await get_global_achievement_percentages(appid)
    global_map = {a["name"]: a["percent"] for a in global_ach}
    
    response = [f"### Achievement Stats for AppID `{appid}`:\n"]
    unlocked = [a for a in player_ach if a.get("achieved") == 1]
    response.append(f"You have unlocked **{len(unlocked)}/{len(player_ach)}** achievements.\n")
    
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
    featured = await get_featured_categories()
    specials = featured.get("specials", {}).get("items", [])
    
    if not specials:
        return "Could not find any featured specials right now."
        
    response = ["### Current Featured Specials on Steam:\n"]
    for item in specials:
        name = item.get("name")
        discount = item.get("discount_percent")
        final = item.get("final_price", 0) / 100
        original = item.get("original_price", 0) / 100
        currency = item.get("currency", "")
        
        response.append(f"- **{name}**: {final:.2f} {currency} (-{discount}%) [~~{original:.2f}~~]")
        
    return "\n".join(response)


if __name__ == "__main__":
    mcp.run()
