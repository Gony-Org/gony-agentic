from app.core.context import auth_token_context
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from typing import Dict, Any, Optional
import uuid
from app.agents.orchestrator import orchestrate_request, orchestrator_team
from app.models.chat import AgentRequest, AgentResponse, ChatRole, ChatHistoryResponse
from app.services.chat_storage import CassandraService
from app.core.nats import nats_service
from app.agents.logs_processing import run_periodic_log_analysis
import asyncio
import logging

async def generate_and_save_title(user_id: str, query: str, response_text: str, session_id: str, db_service: CassandraService):
    try:
        title_prompt = f"Generate a short (3-5 words) title for this chat based on the user query: '{query}' and your response: '{response_text[:100]}...'. Do not use quotes."
        title_response = await orchestrator_team.arun(title_prompt)
        session_name = title_response.content.strip().replace('"', '')
        
        db_service.update_session_name(user_id, session_id, session_name)
    except Exception as e:
        logging.error(f"Error generating title: {e}")

log_analysis_task = None

async def log_analysis_loop():
    while True:
        try:
            await run_periodic_log_analysis()
        except Exception as e:
            logging.error(f"Error in log analysis loop: {e}")
        await asyncio.sleep(900)

router = APIRouter()
cassandra_service = CassandraService() 

@router.on_event("startup")
async def startup_event():
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    cassandra_service.connect()
    await nats_service.connect()
    
    global log_analysis_task
    log_analysis_task = asyncio.create_task(log_analysis_loop())

@router.on_event("shutdown")
async def shutdown_event():
    global log_analysis_task
    if log_analysis_task:
        log_analysis_task.cancel()
        try:
            await log_analysis_task
        except asyncio.CancelledError:
            pass
            
    await nats_service.close()

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@router.post("/query", response_model=AgentResponse)
async def query_agent(
    payload: AgentRequest, 
    request: Request,
    background_tasks: BackgroundTasks,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        token = auth.credentials
        
        if token:
            auth_token_context.set(f"Bearer {token}")
        
        session_id = payload.session_id if payload.session_id else str(uuid.uuid4())
        
        history = cassandra_service.get_session_history(session_id)
        
        is_new_session = len(history) == 0
        session_name = None

        cassandra_service.save_message(session_id, payload.user_id, ChatRole.USER, payload.query, created_at=datetime.utcnow())
        
        result = await orchestrate_request(payload.user_id, payload.query, history)
        
        status = result.get("orchestrator_status", "success")
        
        agent_content_text = ""
        if status == "success":
            agent_content_text = str(result.get("agent_response", ""))
        else:
            agent_content_text = f"Error: {result.get('message', 'Unknown Error')}"

        if is_new_session and status == "success":
             background_tasks.add_task(
                 generate_and_save_title, 
                 payload.user_id, 
                 payload.query, 
                 agent_content_text, 
                 session_id, 
                 cassandra_service
             )
        
        cassandra_service.save_message(
            session_id, 
            payload.user_id, 
            ChatRole.AGENT, 
            agent_content_text, 
            data=result
        )

        nats_subject = f"user.{payload.user_id}.inbox"
        await nats_service.publish(nats_subject, agent_content_text)
        
        import json
        audit_payload = {
            "resource": "chat-bot",
            "action": "message",
            "userId": payload.user_id,
            "role": payload.role or "unknown",
            "workspaceId": payload.workspace_id,
            "metadata": json.dumps({
                "ip": request.client.host if request.client else "unknown",
                "userAgent": request.headers.get("user-agent"),
                "sessionId": session_id,
                "query": payload.query
            })
        }
        logging.info(f"AUDIT LOG: {json.dumps(audit_payload)}"); await nats_service.publish("logs.trace", json.dumps(audit_payload))

        return AgentResponse(
            status=status,
            message=agent_content_text,
            session_id=session_id
        )
        
    except Exception as e:
        import traceback
        logging.error(f"Error in query_agent: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=ChatHistoryResponse)
async def get_user_chat_history(
    user_id: str, 
    limit: int = 20,
    search: Optional[str] = None,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        sessions = cassandra_service.get_user_sessions(user_id, limit=limit, name_filter=search)
        return {"sessions": sessions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
