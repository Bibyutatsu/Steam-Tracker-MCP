import asyncio
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from steam_api import search_games, format_price
from utils import get_country_code

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Steam Price Tracker")

# Detect location on startup
COUNTRY_CODE = get_country_code()
print(f"Server initialized with country code: {COUNTRY_CODE}")

@mcp.tool()
async def get_game_prices(query: str) -> str:
    """
    Search for Steam games by name and return their current prices and details.
    
    Args:
        query: The name of the game to search for (e.g., 'Age of Empires').
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

if __name__ == "__main__":
    # You can run the server directly for testing
    mcp.run()
