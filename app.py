import os
import uvicorn
import logging
import time
from starlette.responses import HTMLResponse, Response, JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from server import mcp
from steam_api import get_and_cache_profile_image

# Configure safe logging (replaces Uvicorn's aggressive access logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("mcp-server")

# Configuration
STEAM_ID = os.getenv("STEAM_ID")
MCP_TOKEN = os.getenv("MCP_TOKEN")

# Create the StreamableHTTP application from the FastMCP instance
app = mcp.streamable_http_app()

# Mount static files for CSS
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

def is_authorized(request):
    """
    Checks if the request is authorized via Header ONLY.
    If MCP_TOKEN is not set in environment, authentication is disabled.
    """
    if not MCP_TOKEN:
        return True
    
    # Strictly check Authorization header (standard practice)
    auth_header = request.headers.get("Authorization")
    if auth_header and (auth_header == f"Bearer {MCP_TOKEN}" or auth_header == MCP_TOKEN):
        return True
    
    # Strictly check custom X-API-Key header
    if request.headers.get("X-API-Key") == MCP_TOKEN:
        return True
        
    return False

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Only protect the MCP communication endpoints
        if request.url.path in ["/mcp", "/sse"]:
            if not is_authorized(request):
                client_ip = request.client.host if request.client else "unknown"
                logger.warning(f"Unauthorized {request.method} to {request.url.path} from {client_ip}")
                return Response("Unauthorized: Missing or invalid Authorization header.", status_code=401)
            
            # Log success without exposing any tokens or query params
            logger.info(f"Authorized {request.method} {request.url.path}")

        response = await call_next(request)
        return response

# Add middleware
app.add_middleware(AuthMiddleware)

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
    """Compatibility alias to ensure both /mcp and /sse work."""
    # Find the original MCP handler provided by FastMCP
    # It might be registered under /mcp or /sse
    for route in app.routes:
        if hasattr(route, "path") and route.path in ["/mcp", "/sse"]:
            # Ensure we don't call ourselves recursively if this route IS mcp_alias
            if route.endpoint != mcp_alias:
                return await route.endpoint(request)
    
    return Response("MCP Endpoint Not Found", status_code=404)

# Add routes to the Starlette application
app.add_route("/", homepage)
app.add_route("/profile_image.png", profile_image)
app.add_route("/mcp", mcp_alias)
app.add_route("/sse", mcp_alias)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    if not MCP_TOKEN:
        logger.critical("SECURITY ALERT: MCP_TOKEN not set! Server will NOT start in insecure public mode.")
        print("\n" + "!"*60)
        print("  CRITICAL SECURITY ERROR: MCP_TOKEN environment variable is missing.")
        print("  Please set MCP_TOKEN to a secure random string for authentication.")
        print("!"*60 + "\n")
        import sys
        sys.exit(1)
    else:
        logger.info("MCP_TOKEN configured. Strict Header Authentication is ACTIVE.")
        
    logger.info(f"Starting Steam Intelligence MCP server on 0.0.0.0:{port}")
    # Disable default access_log to prevent token leaks from URL fallbacks.
    # Restrict forwarded_allow_ips to 127.0.0.1 by default for safety, 
    # but allow it to be configured via env if needed.
    allowed_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips=allowed_ips, access_log=False)
