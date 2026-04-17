import os
import uvicorn
from server import mcp

# Create the SSE application from the FastMCP instance
app = mcp.sse_app()

if __name__ == "__main__":
    # Hugging Face Spaces provides the port via the PORT environment variable
    port = int(os.getenv("PORT", 7860))
    
    print(f"Starting Steam Price Tracker MCP server (SSE) on 0.0.0.0:{port}")
    
    # Run using uvicorn, which is more robust for remote hosting
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        proxy_headers=True, 
        forwarded_allow_ips="*"
    )
