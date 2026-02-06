import httpx
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("API-Client")

@mcp.tool()
async def call_crud_endpoint(
    method: str, 
    url: str, 
    headers: Optional[Dict[str, str]] = None, 
    json_body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute an HTTP request against a REST API endpoint.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: Full URL to calls
        headers: Optional dictionary of headers
        json_body: Optional JSON body for the request
        params: Optional query parameters
        
    Returns:
        JSON response from the API or error details.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=30.0
            )
            
            try:
                return {
                    "status_code": response.status_code,
                    "data": response.json()
                }
            except Exception:
                 return {
                    "status_code": response.status_code,
                    "text": response.text
                }
                
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}
