from datetime import datetime
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
import json

class ChatHistoryModel(Model):
    __keyspace__ = "gony_chat"
    __table_name__ = "chat_history"

    session_id = columns.Text(partition_key=True)
    created_at = columns.DateTime(primary_key=True, clustering_order="ASC", default=datetime.utcnow)
    user_id = columns.Text(required=True)
    role = columns.Text(required=True)
    message = columns.Text(required=True)
    session_name = columns.Text()
    
    def set_data(self, data_dict: dict):
        if data_dict:
            self.data = json.dumps(data_dict)
    
    def get_data(self) -> dict:
        if self.data:
            try:
                return json.loads(self.data)
            except:
                return {}
        return {}

class UserSessionModel(Model):
    __keyspace__ = "gony_chat"
    __table_name__ = "user_sessions"

    user_id = columns.Text(partition_key=True)
    updated_at = columns.DateTime(primary_key=True, clustering_order="DESC", default=datetime.utcnow)
    session_id = columns.Text(primary_key=True)
    session_name = columns.Text()
