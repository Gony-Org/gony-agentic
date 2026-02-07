from contextvars import ContextVar
from typing import Optional

# Context variable to store the authentication token for the current request context
auth_token_context: ContextVar[Optional[str]] = ContextVar("auth_token", default=None)
