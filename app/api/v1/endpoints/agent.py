from app.core.context import auth_token_context
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, Optional
import uuid
from app.agents.orchestrator import orchestrate_request
from app.models.chat import AgentRequest, AgentResponse, ChatRole, ChatHistoryResponse
from app.services.chat_storage import CassandraService
from app.core.nats import nats_service

router = APIRouter()
cassandra_service = CassandraService() 

@router.on_event("startup")
async def startup_event():
    # Attempt connection on startup (optional, helpful for dev)
    cassandra_service.connect()
    await nats_service.connect()

@router.on_event("shutdown")
async def shutdown_event():
    await nats_service.close()

@router.post("/query", response_model=AgentResponse)
async def query_agent(payload: AgentRequest, request: Request):
    """
    Endpoint to interact with the Gony Agentic system (Agno-powered + Cassandra History).
    """
    try:
        # 1. Extract Authentication
        token = request.headers.get("Authorization")
        if not token:
            # Try to get from cookie
            cookie_token = request.cookies.get("auth_token")
            if cookie_token:
                token = f"Bearer {cookie_token}"
        
        # Set context for tools to use
        if token:
            auth_token_context.set(token)
        
        # ... Session Management ...
        session_id = payload.session_id if payload.session_id else str(uuid.uuid4())
        
        # ... Retrieve History ...
        history = cassandra_service.get_session_history(session_id)
        
        # Determine if it's a new session
        is_new_session = len(history) == 0
        session_name = None

        # ... Save User Query ...
        # If new session, we will update the name AFTER generating it, or generate it now?
        # Let's generate it after getting the agent response to have context, or just based on query?
        # User said "orchestrator needs to generate". 
        
        cassandra_service.save_message(session_id, payload.user_id, ChatRole.USER, payload.query, created_at=datetime.utcnow())
        
        # ... Orchestrate ...
        result = await orchestrate_request(payload.user_id, payload.query, history)
        
        status = result.get("orchestrator_status", "success")
        
        # 6. Extract Response Text
        agent_content_text = ""
        if status == "success":
            agent_content_text = str(result.get("agent_response", ""))
        else:
            agent_content_text = f"Error: {result.get('message', 'Unknown Error')}"

        # Generate Title if new session
        if is_new_session and status == "success":
            try:
                # Use the orchestrator's model to generate a title
                # We can't access orchestrator_team directly here efficiently without importing it and initing it?
                # accessing app.agents.orchestrator.orchestrator_team
                from app.agents.orchestrator import orchestrator_team
                
                # Simple prompt for title
                title_prompt = f"Generate a short (3-5 words) title for this chat based on the user query: '{payload.query}' and your response: '{agent_content_text[:100]}...'. Do not use quotes."
                
                # Run independently?
                # orchestrator_team.model is a Gemini instance. 
                # We can use model.generate_content if exposed? 
                # Agno Agent.run() is easier.
                
                title_response = await orchestrator_team.arun(title_prompt)
                session_name = title_response.content.strip().replace('"', '')
            except Exception as e:
                # Fallback
                session_name = payload.query[:30] + "..."
        
        # 7. Save Agent Response (with data for audit) and update session name if new
        cassandra_service.save_message(
            session_id, 
            payload.user_id, 
            ChatRole.AGENT, 
            agent_content_text, 
            data=result, 
            session_name=session_name
        )

        # Publish to NATS (Inbox)
        nats_subject = f"user.{payload.user_id}.inbox"
        await nats_service.publish(nats_subject, agent_content_text)
        
        # Publish Audit Log
        import json
        audit_payload = {
            "resource": "agent_interaction",
            "action": "query",
            "userId": payload.user_id,
            "role": "user", # Defaulting as we don't extract it from token yet
            "workspaceId": None, # Defaulting as we don't have it
            "metadata": json.dumps({
                "ip": request.client.host if request.client else "unknown",
                "userAgent": request.headers.get("user-agent"),
                "sessionId": session_id
            })
        }
        await nats_service.publish("logs.trace", json.dumps(audit_payload))

        # 8. Return Final Response Model
        return AgentResponse(
            status=status,
            message=agent_content_text,
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=ChatHistoryResponse)
async def get_user_chat_history(
    user_id: str, 
    limit: int = 20,
    search: Optional[str] = None
):
    """
    Get all chat sessions for the authenticated user.
    """
    try:
        sessions = cassandra_service.get_user_sessions(user_id, limit=limit, name_filter=search)
        # Convert dict to pydantic model if needed, strictly speaking pydantic handles it if keys match
        return {"sessions": sessions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
