import psycopg
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from app.core.config import settings

# Initialize FastMCP server with a domain-specific name
mcp = FastMCP("APCS-Workflow-Engine")

def execute_read_query(query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Helper to execute read-only queries with standard dictionary rows."""
    try:
        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(query, params)
                return cur.fetchall()
    except Exception as e:
        return

@mcp.tool()
def get_shipment_status(shipment_id: str, org_id: str) -> List[Dict[str, Any]]:
    """
    Get the real-time status of a shipment. 
    Mandatory: org_id is required to ensure multi-tenant isolation.
    """
    query = """
    SELECT s.id, s.status, s.vessel_name, s.arrival_date, w.current_step, w.is_blocked
    FROM shipments s
    JOIN workflows w ON s.id = w.shipment_id
    WHERE s.id = %(shipment_id)s AND s.org_id = %(org_id)s
    """
    return execute_read_query(query, {"shipment_id": shipment_id, "org_id": org_id})

@mcp.tool()
def identify_workflow_blockers(shipment_id: str, org_id: str) -> List[Dict[str, Any]]:
    """
    Identify who is currently holding up a document validation (e.g., Ministry of Health, Bank).
    """
    query = """
    SELECT step_name, assigned_validator, waiting_since, blocker_reason
    FROM workflow_steps
    WHERE shipment_id = %(shipment_id)s 
    AND org_id = %(org_id)s 
    AND status = 'PENDING'
    """
    return execute_read_query(query, {"shipment_id": shipment_id, "org_id": org_id})

@mcp.tool()
def check_compliance_deadlines(org_id: str) -> List[Dict[str, Any]]:
    """
    Check for shipments approaching the Algerian 21-day clearance limit.
    """
    query = """
    SELECT id, vessel_name, discharge_date, 
           (CURRENT_DATE - discharge_date) as days_at_port
    FROM shipments
    WHERE org_id = %(org_id)s 
    AND status!= 'CLEARED'
    AND (CURRENT_DATE - discharge_date) >= 15
    """
    return execute_read_query(query, {"org_id": org_id})

@mcp.tool()
def list_accessible_documents(shipment_id: str, org_id: str, user_role: str) -> List[Dict[str, Any]]:
    """
    List documents for a shipment based on user role.
    Prevents 'Shipping Agents' from seeing 'Customs-Only' risk assessments.
    """
    # Logic: Filter documents by both organization and the security level of the role
    query = """
    SELECT doc_name, doc_type, upload_date, version
    FROM documents
    WHERE shipment_id = %(shipment_id)s 
    AND org_id = %(org_id)s
    AND required_role_level <= %(role_level)s
    """
    # Map roles to numeric levels for easy comparison
    role_map = {"admin": 100, "customs": 80, "agent": 50, "guest": 10}
    level = role_map.get(user_role.lower(), 0)
    
    return execute_read_query(query, {"shipment_id": shipment_id, "org_id": org_id, "role_level": level})

# Removed: run_query (Too dangerous for a secure port system)
# Removed: describe_table (Agent should use domain-specific tools above)