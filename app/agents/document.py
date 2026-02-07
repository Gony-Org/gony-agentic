from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.knowledge import Knowledge
from agno.knowledge.embedder.google import GeminiEmbedder
from agno.vectordb.qdrant import Qdrant
from app.core.config import settings
from app.tools.document_tools import fetch_document_content
import json
from pathlib import Path

# Load endpoints context
# This file provides context about the available API endpoints in the system
endpoints_file_path = settings.BASE_DIR / "crud-endpoints.json"
endpoints_context = ""
try:
    if endpoints_file_path.exists():
        with open(endpoints_file_path, "r") as f:
            # Load and dump to compact string to save tokens
            data = json.load(f)
            endpoints_context = json.dumps(data, separators=(',', ':'))
except Exception as e:
    print(f"Warning: Could not load endpoints context: {e}")

# Qdrant Knowledge Base
# We assume the collection 'documents' is populated with document metadata/chunks
# Note: Keeping GeminiEmbedder as embeddings are separate from chat model
vector_db = Qdrant(
    collection="documents",
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
    https=False, # Assuming internal non-SSL for now based on localhost
    embedder=GeminiEmbedder(api_key=settings.GEMINI_API_KEY),
)

knowledge_base = Knowledge(
    vector_db=vector_db,
    # num_documents determines how many chunks are retrieved
    max_results=5, 
)

# Document Agent
document_agent = Agent(
    name="Document Agent",
    role="Document Researcher & Summarizer",
    model=Claude(id=settings.ANTHROPIC_MODEL, api_key=settings.ANTHROPIC_API_KEY),
    knowledge=knowledge_base,
    tools=[fetch_document_content],
    markdown=True,
    description="You are an expert at finding, reading, and summarizing internal documents.",
    instructions=f"""
    Your goal is to answer user queries by finding relevant documents, reading them, and summarizing the information.
    
    You have access to a Vector Database (Knowledge Base) that contains *references* to documents.
    You also have a tool `fetch_document_content` to read the *actual content* of a document using its URL.
    
    Process:
    1.  **Search**: When a user asks about a topic, the Knowledge Base will automatically retrieve relevant document chunks.
    2.  **Analyze**: Look at the retrieved chunks. They usually contain metadata like the document title and a `url` or `source`.
    3.  **Fetch**: If the chunks don't contain enough full context, use the `fetch_document_content(url=...)` tool to get the full text. 
        - **Critical**: You MUST use this tool to ensure access control is checked. 
        - If the tool returns "ACCESS DENIED", report this to the user clearly.
    4.  **Summarize**: Answer the user's question based on the fetched content.
    
    Context - Available Endpoints:
    The following is a list of API endpoints in the system, which serves as extra context for understanding what 'documents' might refer to (e.g. project specs, reports, etc.):
    {endpoints_context[:10000]} # Truncate to avoid context limit overflow if file is huge
    
    Note: The endpoints data is for *context* only. Do not invent documents. Only use documents found in the Knowledge Base or fetched via tools.
    """,
)
