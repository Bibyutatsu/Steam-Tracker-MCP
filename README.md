# Steam Price Tracker MCP Server

A Model Context Protocol (MCP) server that allows you to search for Steam games and get their current prices, discounts, and store links in your local currency.

## Features
- **Smart Search**: Find matching game titles easily.
- **Auto-Location**: Automatically detects your country to show prices in your local currency.
- **Price Details**: Shows current price, original price, and discount percentage.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Create a `.env` file with your Steam Web API Key:
   ```env
   STEAM_WEB_API_KEY=your_api_key_here
   # Optional: Override country code (e.g., US, IN, GB)
   # STEAM_COUNTRY_CODE=US
   ```

3. **Run the Server**:
   ```bash
   python server.py
   ```

## Usage as MCP Tool

The server exposes one primary tool: `get_game_prices`.

### `get_game_prices(query: str)`
Search for Steam games by name.

**Example Tool Call:**
```json
{
  "name": "get_game_prices",
  "arguments": {
    "query": "Age of Empires"
  }
}
```

## How Location Detection Works
The server uses:
1. `ipify` to get your public IP.
2. `ip-api` to resolve the IP to a country code.
3. The country code is passed to the Steam Store API to return localized pricing and currency.
