import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://taskboard:taskboard@localhost:5432/taskboard"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
LOGIN_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "10"))
