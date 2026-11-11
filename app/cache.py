"""Redis helpers. Every call fails open: if Redis is down the API keeps working, just slower."""

import json
import logging
from typing import Any, cast

import redis

from app.config import LOGIN_RATE_LIMIT, REDIS_URL

log = logging.getLogger(__name__)
client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=1)

TASK_LIST_TTL = 300


def _version_key(project_id: int) -> str:
    return f"tasks:{project_id}:version"


def get_task_list(project_id: int, params: str) -> Any | None:
    """Cached task-list page. The key embeds a per-project version, so bumping the
    version invalidates every cached page for that project at once (no SCAN needed)."""
    try:
        version = client.get(_version_key(project_id)) or "0"
        raw = cast(str | None, client.get(f"tasks:{project_id}:v{version}:{params}"))
        return json.loads(raw) if raw else None
    except redis.RedisError:
        log.warning("redis unavailable, skipping cache read")
        return None


def set_task_list(project_id: int, params: str, value: Any) -> None:
    try:
        version = client.get(_version_key(project_id)) or "0"
        client.set(f"tasks:{project_id}:v{version}:{params}", json.dumps(value), ex=TASK_LIST_TTL)
    except redis.RedisError:
        log.warning("redis unavailable, skipping cache write")


def invalidate_task_list(project_id: int) -> None:
    try:
        client.incr(_version_key(project_id))
    except redis.RedisError:
        # ponytail: stale pages can live up to TASK_LIST_TTL if Redis blips mid-write
        log.warning("redis unavailable, could not invalidate task cache")


def login_allowed(ip: str) -> bool:
    """Fixed-window limiter: LOGIN_RATE_LIMIT attempts per IP per minute."""
    key = f"login:{ip}"
    try:
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60, nx=True)
        attempts, _ = pipe.execute()
        return int(attempts) <= LOGIN_RATE_LIMIT
    except redis.RedisError:
        log.warning("redis unavailable, login rate limit not enforced")
        return True
