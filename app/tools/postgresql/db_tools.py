import psycopg
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from app.core.config import settings

# Initialize FastMCP server with a domain-specific name
mcp = FastMCP("Crud-Schema-Tools")

def get_connection_string() -> str:
    """Enhanced connection string with SSL disabled as requested."""
    base_url = settings.DATABASE_URL
    if "sslmode" not in base_url:
        return f"{base_url}?sslmode=disable"
    return base_url

@mcp.tool()
def list_tables() -> List[str]:
    """
    List all tables in the public schema of the connected database.
    Useful for understanding what data is available.
    """
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """
    try:
        with psycopg.connect(get_connection_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return [row[0] for row in cur.fetchall()]
    except Exception as e:
        return [f"Error listing tables: {str(e)}"]

@mcp.tool()
def describe_table(table_name: str) -> List[Dict[str, Any]]:
    """
    Get the schema definition for a specific table.
    Returns column names, types, and other metadata.
    """
    query = """
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = %(table_name)s
    ORDER BY ordinal_position;
    """
    try:
        with psycopg.connect(get_connection_string()) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(query, {"table_name": table_name})
                return cur.fetchall()
    except Exception as e:
        return [{"error": f"Error describing table {table_name}: {str(e)}"}]