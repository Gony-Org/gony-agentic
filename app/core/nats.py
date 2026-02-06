import nats
from app.core.config import settings

async def connect_nats():
    nc = await nats.connect(settings.NATS_URL)
    return nc