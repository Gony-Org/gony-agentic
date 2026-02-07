import nats
from nats.aio.client import Client as NATS
import logging
from app.core.config import settings

class NatsService:
    def __init__(self):
        self.nc = NATS()
        self.connected = False

    async def connect(self):
        try:
            if not self.connected:
                await self.nc.connect(settings.NATS_URL)
                self.connected = True
                logging.info(f"Connected to NATS at {settings.NATS_URL}")
        except Exception as e:
            logging.error(f"Failed to connect to NATS: {e}")

    async def close(self):
        try:
            if self.connected:
                await self.nc.close()
                self.connected = False
                logging.info("Closed NATS connection")
        except Exception as e:
            logging.error(f"Error closing NATS connection: {e}")

    async def publish(self, subject: str, message: str):
        try:
            if not self.connected:
                logging.warning("NATS not connected. Attempting to connect...")
                await self.connect()
            
            if self.connected:
                await self.nc.publish(subject, message.encode())
                logging.info(f"Published message to {subject}")
            else:
                logging.error(f"Could not publish to {subject}: NATS not connected")
        except Exception as e:
            logging.error(f"Error publishing to {subject}: {e}")

    async def request(self, subject: str, payload: str, timeout: int = 10) -> str:
        try:
            if not self.connected:
                await self.connect()
            
            if self.connected:
                response = await self.nc.request(subject, payload.encode(), timeout=timeout)
                return response.data.decode()
            else:
                logging.error(f"Could not request {subject}: NATS not connected")
                raise ConnectionError("NATS not connected")
        except Exception as e:
            logging.error(f"Error requesting {subject}: {e}")
            raise e

nats_service = NatsService()