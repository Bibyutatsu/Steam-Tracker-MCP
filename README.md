---
title: Steam Tracker MCP
emoji: 🎮
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 🎮 Steam Intelligence MCP Server

[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Space-blue)](https://huggingface.co/spaces/Bibyutatsu/steam-tracker-mcp)
[![Live Demo](https://img.shields.io/badge/%F0%9F%9A%80%20Live-Demo-green)](https://bibyutatsu-steam-tracker-mcp.hf.space/)

Model Context Protocol (MCP) server that transforms Steam into a high-octane intelligence tool. From real-time price tracking and wishlist audits to social monitoring and achievement analytics—give your AI the ultimate gaming edge.

---

## ⚡ Quick Start: 2-Minute Replication

The easiest way to get your own instance running in the cloud:

1.  **Duplicate the Space**: Click the **"Duplicate"** button on the [Bibyutatsu Space](https://huggingface.co/spaces/Bibyutatsu/steam-tracker-mcp).
2.  **Configure Secrets**: In your new Space, go to **Settings > Variables and secrets** and add:
    - `STEAM_WEB_API_KEY`: Your API Key from [Steam Community](https://steamcommunity.com/dev/apikey).
    - `STEAM_ID`: Your 64-bit Steam ID.
    - `MCP_TOKEN`: **(Required for Security)** A secret string used as your Bearer Token.
    - `STEAM_COUNTRY_CODE`: (Optional) Your 2-letter country code (e.g., `US`, `IN`).
3.  **Deploy**: Hit save. The Space will build and launch your private MCP server automatically.

---

## 📁 Project Structure

```text
├── app.py             # Entry point (Uvicorn/Starlette)
├── server.py          # MCP Tool definitions (FastMCP)
├── steam_api.py       # Steam Web API wrapper & Utilities
├── utils.py           # General utility functions
├── templates/         # UI HTML templates
└── static/            # CSS & static assets
```

---

## 🛠️ MCP Configuration
...

## 🛠️ MCP Configuration

### 1. Claude Desktop
Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "steam-tracker": {
      "command": "npx",
      "args": ["-y", "@atishay/mcp-proxy", "--url", "https://bibyutatsu-steam-tracker-mcp.hf.space/sse", "--header", "Authorization: Bearer YOUR_TOKEN"]
    }
  }
}
```

### 2. Cursor / Windsurf
Add a new MCP server in your IDE settings (JSON mode):

```json
"steam-tracker": {
  "url": "https://bibyutatsu-steam-tracker-mcp.hf.space/mcp"
}
/* Note: You must configure the Authorization header in your IDE's MCP settings */
```

### 3. Perplexity
1. Go to **Account Settings > Connectors**.
2. Add a new Connector using the URL: `https://bibyutatsu-steam-tracker-mcp.hf.space/mcp`
3. Set **Authentication Type** to `API Key` (or Bearer Token) and paste your `MCP_TOKEN`.


### 4. Antigravity
Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "steam-tracker": {
      "serverUrl": "https://bibyutatsu-steam-tracker-mcp.hf.space/mcp"
    }
/* Note: Configure headers in your Antigravity MCP settings if available */
  }
}
```

### 🛰️ Tools Catalog

| Category | Tool | Command Your AI to... |
| :--- | :--- | :--- |
| **Store** | `get_game_prices` | "Compare the price of Elden Ring in India vs USA." |
| | `get_top_specials` | "What are the biggest deals on the Steam frontpage?" |
| **Library**| `get_my_wishlist` | "Sort my wishlist by the highest discount percentage." |
| | `analyze_my_library`| "Analyze my library and tell me my top 5 games by playtime." |
| **Social** | `get_friends` | "Is anyone currently playing Counter-Strike?" |
| | `get_player_info` | "Check the status of SteamID 765611..." |
| **Stats** | `get_achievement_stats`| "Show me my rarest achievements in Cyberpunk 2077." |
| | `get_live_player_count`| "How many people are playing Helldivers 2 right now?" |
| **News** | `get_game_news` | "Summarize the latest patch notes for Dota 2." |

---

## 🔧 Customization & Local Development

If you want to modify the logic or add your own tools:

1.  **Fork & Clone**:
    ```bash
    git clone https://github.com/<your-username>/Steam-Tracker-MCP
    cd Steam-Tracker-MCP
    ```
2.  **Environment Setup**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
3.  **Local Testing**:
    Create a `.env` file with your credentials and run:
    ```bash
    python server.py
    ```
4.  **Sync to Cloud**:
    Set your GitHub Repository Secret `HF_TOKEN` (Write access), and every `git push` will automatically update your Hugging Face Space.

---

> [!TIP]
> **Privacy Note**: Most player and achievement tools require the target profile's **"Game Details"** privacy setting to be set to **"Public"**.

> [!IMPORTANT]
> **Ultimate Privacy**: By **Duplicating the Space** and providing your own `MCP_TOKEN` and `STEAM_ID` secrets, you ensure your intelligence data remains private and your API quota is reserved exclusively for your use.

> [!WARNING]
> **Rate Limiting**: This server uses official APIs. For high-volume tools like `get_game_prices`, the server handles batching automatically to prevent Steam API rate-limiting blocks.
