import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from cassandra.cluster import Cluster
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table, create_keyspace_simple
from app.models.chat import ChatMessage, ChatRole
from app.schemas.cassandra_models import ChatHistoryModel

class CassandraService:
    def __init__(self, contact_points=["cassandra"], port=9042, keyspace="gony_chat"):
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
            
            logging.info(f"Connected to Cassandra at {self.contact_points} with keyspace {self.keyspace}")
            
        except Exception as e:
            logging.error(f"Failed to connect to Cassandra: {e}")

    def save_message(self, session_id: str, user_id: str, role: ChatRole, content: str, data: Optional[Dict[str, Any]] = None):
        try:
            # cqlengine handles the insertion
            chat_entry = ChatHistoryModel(
                session_id=session_id,
                user_id=user_id,
                role=role.value,
                message=content,
                timestamp=datetime.utcnow()
            )
            if data:
                chat_entry.set_data(data)
            
            chat_entry.save()
            
        except Exception as e:
            logging.error(f"Error saving message to Cassandra: {e}")
            # Try to reconnect if connection lost?
            # self.connect() 

    def get_session_history(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        try:
            # cqlengine query
            q = ChatHistoryModel.objects(session_id=session_id).all().limit(limit)
            
            messages = []
            for row in q:
                messages.append(ChatMessage(
                    role=ChatRole(row.role),
                    content=row.message,
                    timestamp=row.timestamp
                ))
            return messages
        except Exception as e:
            logging.error(f"Error fetching history from Cassandra: {e}")
            return []
