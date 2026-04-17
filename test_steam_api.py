from steam_api import search_games, format_price
from utils import get_country_code

def test_flow():
    cc = get_country_code()
    print(f"Detected Country Code: {cc}")
    
    query = "Age of Empires"
    print(f"Searching for: {query}")
    
    results = search_games(query, country_code=cc)
    
    if not results:
        print("No results found.")
        return
    
    print(f"Found {len(results)} results:")
    for item in results:
        name = item.get("name")
        appid = item.get("id")
        price = item.get("price")
        
        formatted = format_price(price)
        print(f"- {name} (ID: {appid}): {formatted}")

if __name__ == "__main__":
    test_flow()
