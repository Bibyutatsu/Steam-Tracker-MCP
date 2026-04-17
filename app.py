import os
import uvicorn
from starlette.responses import HTMLResponse, Response
from starlette.staticfiles import StaticFiles
from server import mcp
from steam_api import get_and_cache_profile_image

# Configuration
STEAM_ID = os.getenv("STEAM_ID")

# Create the StreamableHTTP application from the FastMCP instance
app = mcp.streamable_http_app()

# Mount static files for CSS
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

async def homepage(request):
    try:
        with open("templates/index.html", "r") as f:
            content = f.read()
        return HTMLResponse(content)
    except FileNotFoundError:
        return HTMLResponse("<h1>Steam Intelligence</h1><p>Template not found.</p>", status_code=404)

async def profile_image(request):
    img_path = await get_and_cache_profile_image(STEAM_ID)
    if img_path and os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return Response(f.read(), media_type="image/png")
    # Fallback to a transparent 1x1 pixel
    return Response(content=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x04\x00\x00\x00\xb5|\x11\x02\x00\x00\x00\x0bIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfe\x05\xcaG\n\x00\x00\x00\x00IEND\xaeB`\x82", media_type="image/png")

async def mcp_alias(request):
    """Compatibility alias for clients expecting /mcp instead of /sse"""
    # Pipe to the underlying SSE transport provided by FastMCP
    return await app.endpoints["/sse"](request)

# Add routes to the Starlette application
app.add_route("/", homepage)
app.add_route("/profile_image.png", profile_image)
app.add_route("/mcp", mcp_alias)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    print(f"Starting Steam Intelligence MCP server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
