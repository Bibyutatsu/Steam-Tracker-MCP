# Steam Price Tracker MCP Server

A powerful Model Context Protocol (MCP) server that transforms Steam into a personalized intelligence tool for price tracking and wishlist monitoring.

## 🚀 Features

### Core Capabilities
- **Smart Search**: Find any game on the Steam Store with real-time pricing and discount data.
- **Auto-Location**: Automatically detects your country to show prices in your local currency (e.g., ₹ INR, $ USD).

### Personalized Intelligence (New!)
- **Official Wishlist Tracking**: Monitors your Steam wishlist using the official `IWishlistService` Web API.
- **Deal Detection**: Highlights the best discounts and historical lows for games you actually want.
- **Player Intel**: Snapshot of your profile status, current activity, and persona details.

### Remote Access
- **Dual Transport Support**: Run via standard **stdio** (local) or **SSE** (remote/cloud).
- **Hugging Face Ready**: Fully optimized for hosting on Hugging Face Spaces for access from any MCP client (like Claude).

---

## 🛠️ Setup

### 1. Prerequisites
- Python 3.10+
- A Steam Web API Key ([Get it here](https://steamcommunity.com/dev/apikey))
- Your 64-bit Steam ID (e.g., `7656119...`)

### 2. Local Installation
```bash
git clone <repo-url>
cd Steam-Tracker-MCP
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
STEAM_WEB_API_KEY=your_api_key_here
STEAM_ID=your_64_bit_steam_id
# Optional: Force a specific region
# STEAM_COUNTRY_CODE=IN
```

---

## 🕹️ Usage

### Local Execution (Stdio)
```bash
python server.py
```

### Remote Execution (SSE)
To run the server as an SSE endpoint for remote access:
```bash
python app.py
```

---

## 🛠️ MCP Tools

| Tool | Description |
| :--- | :--- |
| `get_game_prices` | Search for games and retrieve localized pricing and store links. |
| `get_my_wishlist` | Fetch your wishlist, show current prices, and sort by best discounts. |
| `get_my_profile` | Get your current Steam status and recently played activity. |

---

## ☁️ Hosting on Hugging Face Spaces

This server is optimized for 24/7 hosting on Hugging Face Spaces using the **Docker SDK**.

1. **Create Space**: Go to [huggingface.co/new-space](https://huggingface.co/new-space) and select the **Docker** SDK.
2. **Upload Files**: Upload all project files EXCEPT `.env` and `.venv` (the `Dockerfile` and `.dockerignore` will handle the rest).
3. **Configure Secrets**: In your Space's **Settings > Variables and secrets**, add:
   - `STEAM_WEB_API_KEY`: Your Steam API Key.
   - `STEAM_ID`: Your 64-bit Steam ID.
   - `STEAM_COUNTRY_CODE`: Your 2-letter country code (optional, e.g., `IN`).
4. **Connect Claude**: Once "Running", add your Space's SSE URL to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "steam-tracker": {
         "url": "https://<your-username>-<space-name>.hf.space/sse"
       }
     }
   }
   ```


---

## 🛰️ How it Works
1. **Discovery**: Uses official `IWishlistService` to securely fetch your specific app inventory.
2. **Pricing**: Dynamically queries the Steam Storefront API using your detected/configured country code.
3. **Transport**: Leverages `FastMCP` and `Uvicorn` to provide a robust, persistent connection for LLM agents.
