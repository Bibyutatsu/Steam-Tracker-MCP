import os
import asyncio
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from steam_api import (
    search_games, format_price, get_wishlist_comprehensive, 
    get_player_summaries, resolve_app_details_batch,
    get_current_players, get_owned_games, get_app_news, resolve_vanity_url,
    get_recently_played_games, get_featured_categories,
    get_library_audit, itad_client, get_social_status, get_rare_achievements,
    get_mutual_games
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

@mcp.tool()
async def get_recent_activity(count: int = 5) -> str:
    """
    Get a breakdown of your gaming activity over the last 14 days.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured."
        
    games = await get_recently_played_games(STEAM_ID, count)
    if not games:
        return "No recent activity found in the last 2 weeks."
        
    response = ["## 🕒 Recent Gaming Activity (Last 14 Days)\n"]
    for g in games:
        name = g.get("name")
        two_weeks = g.get("playtime_2weeks", 0) / 60
        total = g.get("playtime_forever", 0) / 60
        response.append(f"- **{name}**")
        response.append(f"  - Played this session: **{two_weeks:.1f} hours**")
        response.append(f"  - Total playtime: **{total:.1f} hours**")
        
    return "\n".join(response)

@mcp.tool()
async def get_social_intelligence() -> str:
    """
    See which friends are online and what they are playing right now.
    Excellent for finding someone to play with.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured."
        
    statuses = await get_social_status(STEAM_ID)
    if not statuses:
        return "Could not retrieve friend statuses."
        
    response = ["## 👥 Steam Social Intelligence\n"]
    
    in_game = [s for s in statuses if s["status"] == "In-Game"]
    online = [s for s in statuses if s["status"] == "Online"]
    
    if in_game:
        response.append("### 🎮 Currently In-Game")
        for s in in_game:
            response.append(f"- **{s['name']}** is playing **{s['game']}**")
        response.append("")
            
    if online:
        response.append("### 🟢 Online")
        response.append(", ".join([s["name"] for s in online]))
        response.append("")
        
    if not in_game and not online:
        response.append("Everyone is currently offline.")
        
    return "\n".join(response)

@mcp.tool()
async def find_mutual_games(friend_steam_id: str) -> str:
    """
    Compare your library with a friend's to find games you both own.
    Provide the friend's 64-bit SteamID or custom URL name.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured."
        
    # Resolve vanity URL if needed
    target_id = friend_steam_id
    if not friend_steam_id.isdigit():
        resolved = await resolve_vanity_url(friend_steam_id)
        if not resolved:
            return f"Could not resolve SteamID for '{friend_steam_id}'."
        target_id = resolved
        
    mutual = await get_mutual_games(STEAM_ID, target_id)
    if not mutual:
        return "No mutual games found or friend's profile is private."
        
    response = [f"## 🤝 Mutual Games with {friend_steam_id}\n"]
    response.append(f"Found **{len(mutual)}** games in common:")
    for game in sorted(mutual):
        response.append(f"- {game}")
        
    return "\n".join(response)

@mcp.tool()
async def get_achievement_rarity(query: str) -> str:
    """
    Highlight rare achievements you've earned in a specific game.
    Provide game name or AppID.
    """
    if not STEAM_ID:
        return "STEAM_ID not configured."
        
    # Resolve appid
    appid = None
    game_name = query
    if query.isdigit():
        appid = int(query)
    else:
        search = await search_games(query)
        if search:
            appid = search[0]["id"]
            game_name = search[0]["name"]
            
    if not appid:
        return f"Could not find game matching '{query}'."
        
    rare = await get_rare_achievements(STEAM_ID, appid)
    if not rare:
        return f"No rare achievements (< 15%) found for **{game_name}**."
        
    response = [f"## 🏆 Rare Achievements in {game_name}\n"]
    response.append("Achievements you've earned that few others have:")
    for a in rare:
        response.append(f"- **{a['name']}** ({a['percent']}% rarity)")
        if a['description']:
            response.append(f"  - *{a['description']}*")
            
    return "\n".join(response)

@mcp.tool()
async def search_steam_profile(query: str) -> str:
    """
    Look up a Steam user by their name or vanity URL and see their profile overview.
    """
    target_id = query
    if not query.isdigit():
        target_id = await resolve_vanity_url(query)
        if not target_id:
            return f"Could not find a Steam profile for '{query}'."
            
    summaries = await get_player_summaries(target_id)
    if not summaries:
        return f"Profile data for '{query}' is not available."
        
    p = summaries[0]
    name = p.get("personaname")
    url = p.get("profileurl")
    state = p.get("personastate", 0)
    status_map = {0: "Offline", 1: "Online", 2: "Busy", 3: "Away", 4: "Snooze"}
    status = status_map.get(state, "Unknown")
    if "gameid" in p: status = f"Playing **{p.get('gameextrainfo')}**"
    
    response = [f"## 👤 Steam Profile: {name}\n"]
    response.append(f"- **Status**: {status}")
    response.append(f"- **SteamID**: `{target_id}`")
    response.append(f"- **Profile Link**: [View on Steam]({url})")
    
    return "\n".join(response)


# --- CATEGORY 4: PRICE INTELLIGENCE (ITAD) ---

@mcp.tool()
async def get_price_history(appid: int, country: str = None) -> str:
    """
    Get the historical price timeline for a Steam game.
    Excellent for charting how prices have changed over the last 12 months.
    """
    target_country = country or COUNTRY_CODE
    history = await itad_client.get_history(appid, country=target_country)
    if not history:
        return f"No price history found for AppID {appid} in region {target_country}."
    
    response = [f"### 📈 Price History for AppID `{appid}` ({target_country}):\n"]
    response.append("| Date | Store | Price | Original | Cut |")
    response.append("| :--- | :---- | :---- | :------- | :-- |")
    
    # Show last 20 events to keep it readable
    for entry in reversed(history[-20:]):
        ts = entry["timestamp"][:10]
        shop = entry["shop"]["name"]
        deal = entry["deal"]
        price = f"{deal['price']['amount']:.2f} {deal['price']['currency']}"
        reg = f"{deal['regular']['amount']:.2f} {deal['regular']['currency']}"
        cut = f"{deal['cut']}%"
        response.append(f"| {ts} | {shop} | {price} | {reg} | {cut} |")
    
    return "\n".join(response)

@mcp.tool()
async def get_historical_stats(appid: int, country: str = None) -> str:
    """
    Get summary price statistics for a game, including all-time low and current best deal.
    Useful for 'buy-trigger' decisions.
    """
    target_country = country or COUNTRY_CODE
    overview = await itad_client.get_overview(appid, country=target_country)
    if not overview:
        return f"Could not retrieve price overview for AppID {appid}."
    
    prices = overview.get("prices", [])
    if not prices:
        return "No price data available for this game."
        
    main_data = prices[0]
    curr = main_data.get("current", {})
    low = main_data.get("lowest", {})
    
    response = [f"### 💎 Price Intelligence for AppID `{appid}`\n"]
    
    if low:
        low_price = f"{low['price']['amount']:.2f} {low['price']['currency']}"
        low_ts = low.get("timestamp", "").split("T")[0]
        response.append(f"#### 🏆 All-Time Low")
        response.append(f"- **Price**: {low_price}")
        response.append(f"- **Store**: {low['shop']['name']}")
        response.append(f"- **Date**: {low_ts}")
        response.append(f"- **Discount**: -{low.get('cut', 0)}%\n")
        
    if curr:
        curr_price = f"{curr['price']['amount']:.2f} {curr['price']['currency']}"
        response.append(f"#### 🏷️ Current Best Deal")
        response.append(f"- **Price**: {curr_price}")
        response.append(f"- **Store**: {curr['shop']['name']}")
        response.append(f"- **Link**: [Go to Deal]({curr['url']})")
        
    return "\n".join(response)

@mcp.tool()
async def get_global_deals(appid: int, country: str = None) -> str:
    """
    Compare current prices across all major stores (Steam, Epic, GOG, Humble, Fanatical, etc.)
    """
    target_country = country or COUNTRY_CODE
    overview = await itad_client.get_overview(appid, country=target_country)
    if not overview or not overview.get("prices"):
        return f"No store data found for AppID {appid}."
    
    response = [f"### 🌏 Global Price Comparison ({target_country})\n"]
    response.append("| Store | Current Price | Original | Discount | Link |")
    response.append("| :---- | :------------ | :------- | :------- | :--- |")
    
    for shop_deal in overview["prices"]:
        curr = shop_deal.get("current")
        if not curr: continue
        
        shop_name = curr["shop"]["name"]
        price = f"{curr['price']['amount']:.2f} {curr['price']['currency']}"
        reg = f"{curr['regular']['amount']:.2f} {curr['regular']['currency']}"
        cut = f"-{curr['cut']}%"
        url = f"[Link]({curr['url']})"
        
        response.append(f"| {shop_name} | **{price}** | {reg} | {cut} | {url} |")
        
    return "\n".join(response)


if __name__ == "__main__":
    mcp.run()
