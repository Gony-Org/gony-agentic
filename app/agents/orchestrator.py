from typing import List, Dict, Any, Optional
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.team import Team
from app.core.config import settings
from app.agents.db_search_agent import db_search_agent
from app.agents.document import document_agent
from app.agents.logs_processing import logs_processing_agent
from app.models.chat import ChatMessage, ChatRole

# Orchestrator Team
# Uses the 'Supervisor' pattern where the Team leader (model) delegates to members 
# and synthesizes their responses.

# The Team itself acts as the leader.
orchestrator_team = Team(
    name="Gony Orchestrator Team",
    role="Virtual Colleague & Project Manager",
    model=Claude(id=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY),
    # No external intent tool needed; reasoning is internal.
    instructions="""
    You are a Virtual Colleague in the Gony Workspace.
    You have deep knowledge of the workspace state, tasks, members, workflow progress, and document validation workflows.
    
    Your Team Members:
    1. **DB Search Agent**: Specialist in database queries and API data retrieval. capable of searching Projects, Tasks, Users, Workflows, etc.
    2. **Document Agent**: Specialist in finding and summarizing internal documents. Uses the Vector Store (Qdrant) and reads document content.
    3. **Logs Processing Agent**: Specialist in system logs. Can analyze error patterns, performance issues, and historical log data to answer "Why" questions about system behavior.

    Your Goal:
    - Act as a helpful, intelligent colleague.
    - Understand the user's intent based on your knowledge of the workspace domain.
    - **Context Awareness**: Use the provided chat history to understand follow-up questions (e.g., "who is working on THAT task?").

    Process - Internal Reasoning:
    1.  **Analyze the User Query & History**:
        - Is the user asking for data about the workspace (e.g., "status of project X", "who is working on task Y", "Show me my files")?
        - Is this a follow-up to previous messages?
        - Is the user greeting you or asking a general question?
    
    2.  **Act**:
        - **If Data/State/Workflow Query**: You MUST delegate this to the **DB Search Agent**. Do not guess. You need the live data.
        - **If Document/Policy/Spec Query**: You MUST delegate this to the **Document Agent**.
        - **If System Behavior/Error/Log Query**: You MUST delegate this to the **Logs Processing Agent** (e.g. "Why are users failing login?", "Audit tracking").
        - **If General/Greeting**: Respond politely and professionally as a colleague.
        - **If Unknown**: Ask for clarification within the context of project management.

    3.  **Synthesize the Final Response** (after delegation):
        - Receive the structured context from the agents.
        - **CRITICAL**: Translate all technical status codes, agent names, and API errors into natural, helpful language.
        - **NEVER** mention "DB Search Agent", "Document Agent", "Logs Agent", "API endpoints", "JSON output", or "Status Code".
        - If a tool fails or an API is unreachable:
            - Say: "I'm having trouble accessing that information right now. It looks like the system is temporarily unavailable."
            - Do NOT explain *why* (e.g. "NATS connection failed" or "Endpoint 404").
        - If access is denied:
            - Say: "I checked, but you don't have the required permissions to view that information."
        - If the result is **empty** or **not found** (e.g., no tasks, no projects, no documents):
            - Frame it positively and naturally based on the context.
            - **Tasks**: "It looks like your schedule is clear for this month!" or "You don't have any pending tasks."
            - **Workflows**: "There are no active workflows at the moment."
            - **Documents**: "I couldn't find any documents matching that description."
            - **Team/Members**: "It appears this workspace doesn't have any other members yet."
            - **General**: "I checked, but didn't find any information on that."
    
    Tone: Professional, collaborative, warm, and strictly non-technical regarding internal architecture. You are a colleague, not a debugger.
    """,
    markdown=True,
    members=[db_search_agent, document_agent, logs_processing_agent],
)

# Wrapper function
async def orchestrate_request(user_id: str, query: str, history: Optional[List[ChatMessage]] = None):
    """
    Adapter to run the Agno Team from the API, injecting history.
    """
    try:
        # Prepare context from history if available
        # Agno's `run` method often takes `messages` or we can prepend to prompt.
        # Ideally, we load history into the agent's memory, but Agno's `run` is stateless unless `storage` is used.
        # Since we are managing storage externally (CassandraService), we'll pass history as context text or messages.
        
        # Simple approach: Prepend history to the query or instructions logic.
        # Better Agno approach: `team.run(messages=[...])` if supported, or constructing a prompt.
        # Let's format history as a string block for context.
        
        history_context = ""
        if history:
            history_context = "\nRecent Chat History:\n"
            for msg in history:
                history_context += f"- {msg.role.value}: {msg.content}\n"
            
            # Append context to query to ensure the model sees it "in the moment"
            # (Alternatively, inject into system prompt, but query injection is safer for per-request context)
            full_input = f"{history_context}\nCurrent User Query: {query}"
        else:
            full_input = query

        # Run the team
        response = await orchestrator_team.arun(full_input)
        
        return {
            "orchestrator_status": "success",
            "agent_response": response.content,
        }
    except Exception as e:
        return {
            "orchestrator_status": "error",
            "message": f"Team execution failed: {str(e)}"
        }
