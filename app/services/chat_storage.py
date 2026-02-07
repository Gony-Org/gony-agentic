import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from cassandra.cluster import Cluster
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table, create_keyspace_simple
from app.models.chat import ChatMessage, ChatRole
from app.schemas.cassandra_models import ChatHistoryModel, UserSessionModel

class CassandraService:
    def __init__(self, contact_points=None, port=9042, keyspace="gony_chat"):
        if contact_points is None:
            # Try to get from env or default to "cassandra"
            import os
            contact_points = [os.getenv("CASSANDRA_HOST", "cassandra")]
        self.contact_points = contact_points
        self.port = port
        self.keyspace = keyspace
        self.cluster = None
        self.session = None

    def connect(self):
        try:
            # Native connection setup for cqlengine
            # retry_connect=True handles initial connection attempts
            connection.setup(self.contact_points, self.keyspace, protocol_version=3, port=self.port, retry_connect=True)
            
            # Create keyspace if it doesn't exist
            # We need a manual session for keyspace creation usually, or rely on setup to fail?
            # connection.setup usually expects keyspace to exist or we use management functions
            
            # Let's do a manual boostrap for keyspace to be safe, creating a raw cluster first
            cluster = Cluster(self.contact_points, port=self.port)
            session = cluster.connect()
            
            # Create keyspace
            session.execute(f"""
                CREATE KEYSPACE IF NOT EXISTS {self.keyspace}
                WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}}
            """)
            session.shutdown()
            cluster.shutdown()

            # Now fully setup cqlengine with the existing keyspace
            connection.setup(self.contact_points, self.keyspace, protocol_version=3, port=self.port)
            
            # Sync tables
            sync_table(ChatHistoryModel)
            sync_table(UserSessionModel)
            
            logging.info(f"Connected to Cassandra at {self.contact_points} with keyspace {self.keyspace}")
            
        except Exception as e:
            logging.error(f"Failed to connect to Cassandra: {e}")

    def save_message(self, session_id: str, user_id: str, role: ChatRole, content: str, session_name: Optional[str] = None, data: Optional[Dict[str, Any]] = None, created_at: Optional[datetime] = None):
        try:
            timestamp = created_at or datetime.utcnow()
            
            # cqlengine handles the insertion for history
            chat_entry = ChatHistoryModel(
                session_id=session_id,
                user_id=user_id,
                role=role.value,
                message=content,
                created_at=timestamp
            )
            
            if session_name:
                chat_entry.session_name = session_name
                
            if data:
                chat_entry.set_data(data)
            
            chat_entry.save()
            
            # Update User Session Index if request has a name or just to update timestamp
            # Ideally we only update if name is provided or it's a new session, 
            # but updating `updated_at` on every message brings the chat to top.
            
            # Retrieve existing name if not provided (optional optimization, skip for now)
            # Just upsert. If session_name is None, we might want to keep existing?
            # cqlengine columns.Text updates overwrite. 
            
            if session_name:
                 UserSessionModel.create(
                    user_id=user_id,
                    session_id=session_id,
                    updated_at=timestamp,
                    session_name=session_name
                )
            else:
                # If no name provided, we only want to update timestamp.
                # However, inserting into UserSessionModel with same PK (user_id, updated_at, session_id) is insert.
                # But updated_at changes! So we get a new row if we just insert? 
                # Wait, Clustering Keys: updated_at, session_id.
                # If we insert with new updated_at, we get a NEW row for the same session? YES.
                # That's bad. We want one row per session per user, ordered by updated_at.
                
                # Cassandra modeling for "User's threads sorted by recent":
                # PK: (user_id), CK: (updated_at DESC, session_id)
                # To "move" a thread to top, we must DELETE old row and INSERT new row.
                # This is expensive. For now, let's just insert for NEW sessions or explicit updates?
                # Or maybe just don't update `updated_at` on every message for this MVP to avoid read-before-write.
                
                # Simplified approach for now:
                # Only insert into UserSessionModel when we have a name (creation time).
                pass

        except Exception as e:
            logging.error(f"Error saving message to Cassandra: {e}")

    def get_session_history(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        try:
            # cqlengine query
            q = ChatHistoryModel.objects(session_id=session_id).all().limit(limit)
            
            messages = []
            for row in q:
                messages.append(ChatMessage(
                    role=ChatRole(row.role),
                    content=row.message,
                    timestamp=row.created_at
                ))
            return messages
        except Exception as e:
            logging.error(f"Error fetching history from Cassandra: {e}")
            return []

    def get_user_sessions(self, user_id: str, limit: int = 20, name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            # Check UserSessionModel
            # Since filtering by non-key column is inefficient/hard in Cassandra, 
            # we fetch user's sessions and filter in Python for this MVP.
            # Ideally we'd use SASI index or separate table for search.
            
            q = UserSessionModel.objects(user_id=user_id)
            # Fetch a bit more if filtering
            if name_filter:
                q = q.limit(limit * 5) 
            else:
                q = q.limit(limit)
                
            results = []
            for row in q:
                if name_filter:
                    # Case-insensitive partial match
                    if not row.session_name or name_filter.lower() not in row.session_name.lower():
                        continue
                
                results.append({
                    "session_id": row.session_id, 
                    "session_name": row.session_name, 
                    "updated_at": row.updated_at
                })
                
                if len(results) >= limit:
                    break
            
            return results
        except Exception as e:
             logging.error(f"Error fetching user sessions: {e}")
             return []

    def update_session_name(self, user_id: str, session_id: str, new_name: str):
        try:
            # We need to find the row first because updated_at is part of PK
            # Use allow_filtering since we don't have updated_at
            row = UserSessionModel.objects(user_id=user_id, session_id=session_id).allow_filtering().first()
            if row:
                row.update(session_name=new_name)
        except Exception as e:
            logging.error(f"Error updating session name: {e}")
