import aioredis
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from common import config

# ==== sql ====
engine_kwargs = {}

if config.DB_TYPE == 'sqlite':
    engine_kwargs.update(connect_args={"check_same_thread": False})
elif config.DB_TYPE == 'postgresql':
    engine_kwargs.update(pool_size=10, max_overflow=20)

engine = create_engine(config.DB_URI, **engine_kwargs, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==== redis ====
EVENT_QUEUE_KEY = "events_pq"
TTL_ONE_HOUR = 3600
redis = aioredis.from_url(config.REDIS_URI)
