from typing import List, Dict, Any, Optional
from agno.agent import Agent
from agno.models.google import Gemini
from agno.team import Team
from app.core.config import settings
from app.agents.db_search_agent import db_search_agent
from app.models.chat import ChatMessage, ChatRole

# Orchestrator Team
# Uses the 'Supervisor' pattern where the Team leader (model) delegates to members 
# and synthesizes their responses.

team_leader = Agent(
    name="Team Leader",
    role="Virtual Colleague & Project Manager",
    model=Gemini(id=settings.GEMINI_MODEL, api_key=settings.GEMINI_API_KEY),
    # No external intent tool needed; reasoning is internal.
    instructions="""
    You are a Virtual Colleague in the Gony Workspace.
    You have deep knowledge of the workspace state, tasks, members, workflow progress, and document validation workflows.
    
    Your Team Members:
    1. **DB Search Agent**: Specialist in database queries and API data retrieval. capable of searching Projects, Tasks, Users, Workflows, etc.

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
        - **If General/Greeting**: Respond politely and professionally as a colleague.
        - **If Unknown**: Ask for clarification within the context of project management.

    3.  **Synthesize the Final Response** (after delegation):
        - Receive the structured context from the DB Search Agent.
        - Translate the technical status (success, access_denied, not_found) into a natural, helpful response.
        - "I checked the system, and..."
        - If access is denied, explain it as a policy enforcement ("You don't have the required permissions for that resource.") rather than a system error.
    
    Tone: Professional, collaborative, and context-aware.
    """,
    markdown=True,
    show_tool_calls=True
)

orchestrator_team = Team(
    name="Gony Orchestrator Team",
    team_leader=team_leader,
    members=[db_search_agent],
    show_tool_calls=True
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
        response = orchestrator_team.run(full_input)
        
        return {
            "orchestrator_status": "success",
            "agent_response": response.content,
        }
    except Exception as e:
        return {
            "orchestrator_status": "error",
            "message": f"Team execution failed: {str(e)}"
        }
