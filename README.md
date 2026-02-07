# Gony Agentic Service

The **Gony Agentic Service** is an intelligent, multi-agent system designed to act as a virtual colleague within the Gony workspace. It leverages **Agentic RAG (Retrieval-Augmented Generation)**, **SQL/CRUD capabilities**, and **autonomous log analysis** to assist users, automate workflows, and monitor system health.

Built with **FastAPI**, **Agno (Phidata)**, **Qdrant**, and **NATS**, it integrates seamlessly with the Gony ecosystem.

---

## 🏗️ System Architecture

The system follows a **Hub-and-Spoke** agentic architecture where a central **Orchestrator** delegates tasks to specialized sub-agents. It interacts with the outside world via REST APIs (for user chat) and NATS (for event-driven logs and notifications).

```mermaid
graph TD
    User[User / Frontend] -->|REST API| API[FastAPI /query]
    API --> Orchestrator
    
    subgraph "Agent Team"
        Orchestrator[Orchestrator Agent]
        DBAgent[DB Search Agent]
        DocAgent[Document Agent]
        LogsAgent[Logs Processing Agent]
    end
    
    Orchestrator -->|Delegates| DBAgent
    Orchestrator -->|Delegates| DocAgent
    Orchestrator -->|Delegates| LogsAgent
    
    DBAgent -->|CRUD API| ExternalAPI[Core Backend API]
    DocAgent -->|Vector Search| Qdrant[Qdrant (Vectors)]
    LogsAgent -->|NATS| NATS[NATS Broker]
    
    NATS -->|Logs Stream| LogsAgent
    LogsAgent -->|Suggestions| NATS
```

---

## 🤖 Agents & Roles

### 1. Orchestrator Agent (The "Team Leader")
*   **Role**: Virtual Colleague & Project Manager.
*   **Responsibility**: The user-facing interface. It receives natural language queries, understands intent, delegates work to the specialist agents, and synthesizes the final friendly response.
*   **Persona**: Warm, professional, non-technical. Handles errors gracefully (e.g., interprets "404 Not Found" as "Free Schedule").

### 2. DB Search Agent (The "Data Specialist")
*   **Role**: Database & API Specialist.
*   **Responsibility**: Fetching structured data (Projects, Tasks, Users, Workflows) from the Core Backend.
*   **Tools**:
    *   `list_tables()`: Explore available data structures.
    *   `call_crud_endpoint(method, url)`: Execute GET requests against the `CRUD_API_URL` to retrieve live data.
*   **Knowledge**: Has access to `crud-endpoints.json` context to map user questions to specific API endpoints.

### 3. Document Agent (The "Librarian")
*   **Role**: Knowledge Base Specialist (RAG).
*   **Responsibility**: Answering questions based on unstructured documents (PDFs, Wikis, Guidelines) stored in the Vector Database.
*   **Tools**:
    *   `fetch_document_content(url)`: Retrieves the full text of a document found via search.
*   **Knowledge**: Connected to **Qdrant** (`documents` collection) to perform semantic search on company knowledge.

### 4. Logs Processing Agent (The "System Analyst")
*   **Role**: Autonomous Log Analyst & Consultant.
*   **Responsibility**: Runs in the background (periodically) to monitor system health, detect inefficiencies, and suggest improvements.
*   **Tools**:
    *   `fetch_logs(limit, filter)`: Retrieves recent system logs via NATS.
    *   `publish_suggestion(json)`: Broadcasts actionable insights to users or the system via NATS channels.
*   **Workflow**:
    1.  Fetches recent logs.
    2.  Analyzes for **Resource Access** (permissions), **Action Patterns** (manual bottlenecks), and **Role Issues**.
    3.  Generates a "Proposal" or "Message".
    4.  Publishes it to `user.{id}.inbox` via NATS.

---

## 🔄 Key Workflows

### A. User Chat Query
1.  **Input**: User asks "What are my tasks for this month?" via `POST /api/v1/agent/query`.
2.  **Routing**: The **Orchestrator** analyzes the intent.
3.  **Delegation**: Orchestrator calls **DB Search Agent**.
4.  **Execution**: DB Agent looks up `GET /tasks`, calls the API, and returns JSON data.
5.  **Synthesis**: Orchestrator receives the JSON, formats it into a friendly message ("You have 3 tasks..."), and returns it to the user.

### B. Autonomous Log Analysis
1.  **Trigger**: Validated by `run_periodic_log_analysis()` background task (runs every 15 mins).
2.  **Fetch**: **Logs Agent** requests logs from NATS `logs.retrieve`.
3.  **Reasoning**: Agent identifies that User X got 5 "Access Denied" errors on Project Y.
4.  **Suggestion**: Agent formulates a proposal: "I suggest granting User X 'Viewer' access to Project Y."
5.  **Notification**: Agent publishes this suggestion to the admin's inbox via NATS.

---

## 🛠️ Technology Stack

*   **Framework**: Python 3.12, FastAPI
*   **LLM Orchestration**: [Agno (formerly Phidata)](https://github.com/agno-agi/agno)
*   **LLM Provider**: Anthropic Claude (via `agno.models.anthropic`)
*   **Vector Database**: Qdrant (for RAG and Memory)
*   **Messaging**: NATS (for async logs and event-driven communication)
*   **Database**: PostgreSQL (via internal CRUD API), Cassandra (for Chat History)

## ⚙️ Configuration

The service is configured via environment variables (loaded from `.env`).

| Variable | Description |
| :--- | :--- |
| `ANTHROPIC_API_KEY` | Key for Claude models. |
| `CRUD_API_URL` | Base URL for the external Core Backend (e.g., `http://host.docker.internal:8080`). |
| `NATS_URL` | URL for NATS broker. |
| `QDRANT_HOST` | Hostname for Vector DB. |

---

## 🚀 Getting Started

1.  **Environment Setup**:
    ```bash
    cp .env.example .env
    # Fill in ANTHROPIC_API_KEY and CRUD_API_URL
    ```

2.  **Run with Docker**:
    ```bash
    docker-compose up --build
    ```

3.  **Access**:
    *   API Docs: `http://localhost:8001/docs`
    *   Agent Query: `POST /api/v1/agent/query`
