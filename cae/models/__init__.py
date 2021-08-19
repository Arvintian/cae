from cae.config import config
import redis

redis_client: redis.Redis = redis.Redis.from_url(url=config.get("REDIS_URL"), health_check_interval=30)
