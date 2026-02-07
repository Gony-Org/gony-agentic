import os
import sys

# Add app to path
sys.path.append(os.getcwd())

from app.services.chat_storage import CassandraService
from app.schemas.cassandra_models import ChatHistoryModel, UserSessionModel
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table
from datetime import datetime

def migrate():
    print("Starting migration of Chat History to User Sessions...")
    
    # Initialize connection
    # Assuming standard docker-compose service name 'cassandra' or localhost if mapped
    # If running from OUTSIDE docker (on host), use localhost and port 9042
    # Ensure this matches where the script runs. If running via `docker-compose exec app ...` use 'cassandra'.
    # If using run_command on user's machine, we need to map the port. docker-compose maps 9042:9042.
    
    # Try localhost first since we are running on host machine? 
    # The user is running `docker-compose up`. The environment is macos.
    # The agent functionality `run_command` runs on the host. 
    # Port 9042 is exposed in docker-compose.yml.
    
    try:
        connection.setup(['127.0.0.1'], "gony_chat", protocol_version=3, port=9042, retry_connect=True)
        print("Connected to Cassandra.")
        
        sync_table(UserSessionModel)
        
        # Scan all chat history
        # Note: This is efficient only for small datasets. For large production, use Spark or valid tool.
        print("Scanning ChatHistoryModel...")
        all_chats = ChatHistoryModel.objects.all()
        
        sessions = {}
        
        for chat in all_chats:
            sid = chat.session_id
            uid = chat.user_id
            ts = chat.created_at
            
            # We want the *latest* timestamp for the session
            if sid not in sessions:
                sessions[sid] = {
                    "user_id": uid,
                    "updated_at": ts,
                    "session_name": chat.session_name or "Untitled Chat"
                }
            else:
                if ts > sessions[sid]["updated_at"]:
                    sessions[sid]["updated_at"] = ts
                # Prefer a non-null name if we found one
                if chat.session_name and sessions[sid]["session_name"] == "Untitled Chat":
                    sessions[sid]["session_name"] = chat.session_name
        
        print(f"Found {len(sessions)} unique sessions.")
        
        count = 0
        for sid, data in sessions.items():
            # Check if exists (inefficient loop but safe)
            # Actually, `create` will insert.
            # We just insert.
            
            # Since we want to avoid duplicates if we run this multiple times? 
            # We can't easily check for existence with (user, updated_at, session) efficiently if we don't know updated_at accurately matching.
            
            # Just insert.
            UserSessionModel.create(
                user_id=data["user_id"],
                session_id=sid,
                updated_at=data["updated_at"],
                session_name=data["session_name"]
            )
            count += 1
            
        print(f"Migrated {count} sessions to UserSessionModel.")
            
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
