---
title: Steam Tracker MCP
emoji: 🎮
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 🎮 Steam Intelligence MCP Server

A state-of-the-art Model Context Protocol (MCP) server that transforms Steam into a high-octane intelligence tool. From real-time price tracking and wishlist audits to social monitoring and achievement analytics—give your AI the ultimate gaming edge.

---

## 🚀 Key Features

### 💎 Performance & Intelligence
- **Market Sentinel**: Real-time localized pricing (₹, $, €, etc.) using automatic region detection.
- **Library Architect**: Deep-dive analysis of your owned games, calculating total playtime and backlog trends.
- **Social Pulse**: Live monitoring of friend activity and persona status.
- **Achievement Rarity**: Compare your personal 100% unlocks against global player density.

### ☁️ Deployment Excellence
- **Zero-Config Hosting**: Native support for Hugging Face Spaces (Docker).
- **Dual-Mode Transport**: Seamlessly switch between **Stdio** (Local) and **SSE** (Cloud) protocols.
- **Auto-Sync**: Built-in GitHub Actions to keep your cloud instance in-sync with your code changes.

---

## ⚡ Quick Start: 2-Minute Replication

The easiest way to get your own instance running in the cloud:

1.  **Duplicate the Space**: Click the **"Duplicate"** button on the original Hugging Face Space.
2.  **Configure Secrets**: In your new Space, go to **Settings > Variables and secrets** and add:
    - `STEAM_WEB_API_KEY`: Your API Key from [Steam Community](https://steamcommunity.com/dev/apikey).
    - `STEAM_ID`: Your 64-bit Steam ID.
    - `STEAM_COUNTRY_CODE`: (Optional) Your 2-letter country code (e.g., `US`, `IN`).
3.  **Deploy**: Hit save. The Space will build and launch your private MCP server automatically.

---

## 🛠️ MCP Configuration

Add this to your `claude_desktop_config.json` (or equivalent) to unlock **12+ advanced gaming tools**:

```json
{
  "mcpServers": {
    "steam-intelligence": {
      "url": "https://<your-username>-<your-space-name>.hf.space/sse"
    }
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
> **Rate Limiting**: This server uses official APIs. For high-volume tools like `get_game_prices`, the server handles batching automatically to prevent Steam API rate-limiting blocks.
