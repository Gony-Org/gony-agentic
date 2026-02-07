import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from agno.agent import Agent
from agno.models.anthropic import Claude

from app.core.config import settings
from app.tools.postgresql.db_tools import list_tables, describe_table
from app.tools.api_client import call_crud_endpoint

# Load context for instructions
CRUD_CONTEXT: List[Dict[str, Any]] = []
try:
    context_path = settings.BASE_DIR / "read-endpoints.json"
    if context_path.exists():
        with open(context_path, "r") as f:
            CRUD_CONTEXT = json.load(f)
except Exception as e:
    logging.error(f"Error loading CRUD context: {e}")

# Context string for the agent
context_str = json.dumps(CRUD_CONTEXT, indent=2)

db_search_agent = Agent(
    name="DB Search Agent",
    role="Database and API Specialist",
    model=Claude(id=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY),
    tools=[list_tables, describe_table, call_crud_endpoint],
    description="You are an intelligent agent responsible for finding information in a database using a set of CRUD API endpoints.",
    instructions=f"""
    Your goal is to answer user queries by retrieving data from the database via the available API endpoints.

    You have access to:
    1.  `list_tables()` and `describe_table(table_name)`: Use these to understand the database schema if needed to map the query to the data model.
    2.  `call_crud_endpoint(method, url, ...)`: Use this to execute the actual API call to get data.

    Available API Endpoints Context:
    {context_str}

    Process:
    1.  Analyze the user query.
    2.  If helpful, use `list_tables` to see what tables exist (e.g. to confirm if 'projects' or 'workspaces' exist).
    3.  Select the best matching endpoint from the 'Available API Endpoints Context'.
    4.  Construct the full URL (base: {settings.CRUD_API_URL}) and parameters.
    5.  Call `call_crud_endpoint` to execute the request.
    
    CRITICAL: Error Analysis & Reporting
    - If the API call fails, do NOT just say "failed". You must analyze the status code and return a specific CONTEXT object.
    - **401/403 (Unauthorized/Forbidden)**:
        - Return: {{ "status": "access_denied", "reason": "User does not have permission", "endpoint": "..." }}
        - Explain that the resource exists but access is restricted.
    - **404 (Not Found)**:
        - Return: {{ "status": "not_found", "reason": "Resource does not exist", "endpoint": "..." }}
        - Explain that the specific item requested (e.g., project ID) was not found.
    - **500 (Server Error)**:
        - Return: {{ "status": "server_error", "details": "..." }}

    - **200/201 (Success)**:
        - Return the data found clearly formatted JSON.

    Output Rule:
    - Provide the raw data or the structured error context. 
    - Do NOT try to be a chatbot. Just report the facts/data/errors for the Team Leader to synthesize.
    """,
    markdown=True,
)
