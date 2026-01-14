import redis.asyncio as aioredis
from .env import ENV

redis_client = aioredis.Redis(host=ENV.redis_host, port=ENV.redis_port, decode_responses=True)