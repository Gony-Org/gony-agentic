from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.knowledge import Knowledge
from agno.knowledge.embedder.google import GeminiEmbedder
from agno.vectordb.qdrant import Qdrant
from app.core.config import settings
from app.core.nats import nats_service
from app.models.logs import LogRetrieveResponse, LogSuggestion
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# Tool to fetch logs via NATS
async def fetch_logs(
    limit: int = 10,
    orderBy: str = "timestamp",
    orderDirection: str = "desc",
    userId: Optional[str] = None,
    role: Optional[str] = None,
    resource: Optional[str] = None,
    workspaceId: Optional[str] = None,
    fromTimestamp: Optional[str] = None,
    toTimestamp: Optional[str] = None
) -> str:
    """
    Fetch logs from the central logging service via NATS request-reply.
    
    Args:
        limit: Max number of logs (default 10)
        orderBy: Field to sort by (timestamp, role, userId, resource)
        orderDirection: asc or desc
        userId: Filter by user ID
        role: Filter by role
        resource: Filter by resource
        workspaceId: Filter by workspace ID
        fromTimestamp: ISO-8601 timestamp
        toTimestamp: ISO-8601 timestamp
        
    Returns:
        JSON string of LogRetrieveResponse containing logs and metadata.
        Example Response:
        {
          "success": true,
          "message": "Logs retrieved successfully",
          "count": 1,
          "totalCount": 150,
          "logs": [
            {
              "id": "550e8400-e29b-41d4-a716-446655440000",
              "timestamp": "2024-02-07T09:20:00Z",
              "resource": "users",
              "action": "LOGIN",
              "userId": "user-123",
              "role": "user",
              "workspaceId": "ws-1",
              "metadata": "{}"
            }
          ]
        }
    """
    request_payload = {
        "limit": limit,
        "orderBy": orderBy,
        "orderDirection": orderDirection,
        "userId": userId,
        "role": role,
        "resource": resource,
        "workspaceId": workspaceId,
        "fromTimestamp": fromTimestamp,
        "toTimestamp": toTimestamp
    }
    # Remove None values
    request_payload = {k: v for k, v in request_payload.items() if v is not None}
    
    try:
        response_str = await nats_service.request("logs.retrieve", json.dumps(request_payload))
        return response_str
    except Exception as e:
        return json.dumps({"success": False, "message": f"Error fetching logs: {str(e)}", "logs": [], "count": 0, "totalCount": 0})

# Tool to publish suggestion
async def publish_suggestion(suggestion: str, target_user_ids: Optional[str] = None):
    """
    Publish a suggestion (JSON string) to NATS.
    Args:
        suggestion: The JSON string of the suggestion.
        target_user_ids: Comma-separated list of user IDs to send the suggestion to (e.g. "user-1,user-2").
                        If None, publishes to general logs insights channel.
    """
    try:
        if target_user_ids:
            # Split and clean IDs
            user_ids = [uid.strip() for uid in target_user_ids.split(",") if uid.strip()]
            for uid in user_ids:
                subject = f"user.{uid}.inbox"
                await nats_service.publish(subject, suggestion)
            return f"Suggestion published to {len(user_ids)} users."
        else:
            await nats_service.publish("logs.insights", suggestion)
            return "Suggestion published to general insights channel."
    except Exception as e:
        return f"Error publishing suggestion: {e}"

# Load endpoints context
endpoints_file_path = settings.BASE_DIR / "crud-endpoints.json"
endpoints_context = ""
try:
    if endpoints_file_path.exists():
        with open(endpoints_file_path, "r") as f:
            data = json.load(f)
            endpoints_context = json.dumps(data, separators=(',', ':'))
except Exception as e:
    logging.warning(f"Could not load endpoints context: {e}")

# Qdrant Knowledge Base for Logs Insights
vector_db = Qdrant(
    collection="logs_insights",
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
    https=False,
    embedder=GeminiEmbedder(api_key=settings.GEMINI_API_KEY),
)

logs_knowledge_base = Knowledge(
    vector_db=vector_db,
    # num_documents determines how many chunks are retrieved
    max_results=5, 
)

# Logs Processing Agent
logs_processing_agent = Agent(
    name="Log Logic Agent",
    role="System Log Analyst & Consultant",
    model=Claude(id=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY),
    knowledge=logs_knowledge_base,
    tools=[fetch_logs, publish_suggestion],
    markdown=True,
    description="You are an autonomous agent that monitors system logs, identifies patterns, and suggests improvements.",
    instructions=f"""
    Your goal is to analyze system logs to find inefficiencies, anomalies, or repeated errors, and suggest actionable fixes.
    
    Process:
    1.  **Fetch Logs**: Use `fetch_logs` to get recent activity. Focus on errors, repeated actions, or specific workspace patterns.
    2.  **Analyze**: Group logs by Workspace, Role, or Resource. Look for:
        - Permission errors (Access Denied) -> Suggest role updates.
        - Repeated failures -> Suggest configuration fixes.
        - High frequency of manual actions -> Suggest automation.
        - Anomalies -> Flag potential security or performance issues.
    3.  **Cross-Reference**: Use your Knowledge Base (previous insights) and the available `endpoints` context to understand what the logs specifically mean in this system.
    4.  **Generate Suggestions**: Output two types of insights:
        - **Message**: General observations or alerts (e.g., "High latency detected in workspace X").
        - **Proposal**: Specific actionable changes that the user can Accept or Reject.
            - Provide a clear, natural language suggestion (e.g., "I suggest we enable auto-assignment of the 'admin' role for new users in this workspace to prevent permission errors.").
    5.  **Publish**: Use `publish_suggestion` to broadcast.
        - **Critical**: Identify ALL `user_id`s involved in the pattern (e.g. multiple users failing permission checks).
        - Pass them as a comma-separated string to `target_user_ids` (e.g. "user-123,user-456") to ensure they all receive the message in their `user.{id}.inbox`.
    
    Context - Available Endpoints:
    {endpoints_context[:10000]}
    
    Memory Handling:
    - You utilize Qdrant to store your reasoning results.
    """,
)

# Background Periodic Task
async def run_periodic_log_analysis():
    """
    Fetches recent logs and runs the agent to analyze them.
    This should be called periodically (e.g., every 10 minutes).
    """
    try:
        logging.info("Starting periodic log analysis...")
        
        # 1. Fetch Logs (last 10 minutes implicitly via limit or time range if API supports)
        # For this implementation, we just fetch the last 50 logs to analyze recent patterns.
        # Ideally, calculate fromTimestamp = now - 10mins
        
        logs_json = await fetch_logs(limit=50, orderBy="timestamp", orderDirection="desc")
        
        # 2. Run Agent
        # We instruct the agent to analyze the provided logs.
        # Since 'agent.run' or similar isn't directly exposed as 'input' -> 'output', 
        # we can use the `print_response` or `run` method if available on the Agno Agent.
        # We'll use `agent.run()` which returns a RunResponse.
        
        prompt = f"""
        analyze the following system logs and generate insights or suggestions.
        Focus on anomalies, repeated errors, or efficiency improvements.
        
        Logs Data:
        {logs_json}
        """
        
        # Use stream=False for background processing
        response = await logs_processing_agent.arun(prompt)
        
        logging.info(f"Log analysis complete. Agent Response: {response.content}")
        
    except Exception as e:
        logging.error(f"Error in periodic log analysis: {e}")
