import contextlib
from typing import AsyncGenerator

from pgvector.asyncpg import register_vector
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@contextlib.asynccontextmanager
async def get_db(settings: object) -> AsyncGenerator[AsyncSession, None]:
    SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOST_NAME}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"

    engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

    @event.listens_for(engine.sync_engine, "connect")
    async def connect(dbapi_connection, connection_record):
        await register_vector(dbapi_connection)

    db = SessionLocal()
    await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    try:
        yield db
    finally:
        await db.close()
