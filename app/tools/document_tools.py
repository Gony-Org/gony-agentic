from app.tools.api_client import call_crud_endpoint
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any

# Create a separate tool definition for the agent to use
# We can mistakenly reuse the same mcp object but it's cleaner to define a function 
# that the agent can import.
# Or if we want to expose it as an MCP tool, we wrap it.
# The user said "make it's tools in the tools folder".

async def fetch_document_content(url: str) -> str:
    """
    Fetches the content of a document from the internal API.
    Use this tool when you need to read the full content of a document found in the vector store.
    
    Args:
        url: The full URL to the document endpoint (usually provided by the vector store search result).
        
    Returns:
        The text content of the document or an error message if access is denied.
    """
    # By default, api_client uses the context's auth token
    result = await call_crud_endpoint(method="GET", url=url)
    
    if result.get("status_code") == 200:
        return str(result.get("data", ""))
    elif result.get("status_code") in [401, 403]:
        return "ACCESS DENIED: You do not have permission to view this document."
    else:
        return f"Error fetching document: {result.get('status_code')} - {result.get('text', '')}"
