from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import uuid
from app.agents.orchestrator import orchestrate_request
from app.models.chat import AgentRequest, AgentResponse, ChatRole
from app.services.chat_storage import CassandraService

router = APIRouter()

# Dependency for storage service (singleton-like)
# In production, use properly configured DI
cassandra_service = CassandraService() 

@router.on_event("startup")
async def startup_event():
    # Attempt connection on startup (optional, helpful for dev)
    cassandra_service.connect()

@router.post("/query", response_model=AgentResponse)
async def query_agent(payload: AgentRequest):
    """
    Endpoint to interact with the Gony Agentic system (Agno-powered + Cassandra History).
    """
    try:
        # 1. Session Management
        session_id = payload.session_id if payload.session_id else str(uuid.uuid4())
        
        # 2. Retrieve History
        history = cassandra_service.get_session_history(session_id)
        
        # 3. Save User Query
        cassandra_service.save_message(session_id, payload.user_id, ChatRole.USER, payload.query)
        
        # 4. Orchestrate with History Context
        result = await orchestrate_request(payload.user_id, payload.query, history)
        
        status = result.get("orchestrator_status", "success")
        
        # 5. Extract Response Text
        agent_content_text = ""
        if status == "success":
            agent_content_text = str(result.get("agent_response", ""))
        else:
            agent_content_text = f"Error: {result.get('message', 'Unknown Error')}"

        # 6. Save Agent Response (with data for audit)
        cassandra_service.save_message(session_id, payload.user_id, ChatRole.AGENT, agent_content_text, data=result)
        
        # 7. Return Final Response Model
        return AgentResponse(
            status=status,
            message=agent_content_text,
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
