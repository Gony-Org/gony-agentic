from app.core.config import settings

print(f"QDRANT_HOST: {settings.QDRANT_HOST}")
print(f"NATS_URL: {settings.NATS_URL}")
print(f"CRUD_API_URL: {settings.CRUD_API_URL}")
print(f"ANTHROPIC_MODEL: {settings.ANTHROPIC_MODEL}")

if settings.CRUD_API_URL == "http://localhost:8080":
    print("WARNING: CRUD_API_URL usage default hardcoded value or localhost")
elif settings.CRUD_API_URL == "http://host.docker.internal:8080":
    print("SUCCESS: CRUD_API_URL loaded from .env")
else:
    print(f"CRUD_API_URL is {settings.CRUD_API_URL}")
