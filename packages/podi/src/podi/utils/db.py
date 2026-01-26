import contextlib
from typing import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def get_db_generator(settings: object) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"

    engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

    db = SessionLocal()

    @contextlib.asynccontextmanager
    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        try:
            yield db
        finally:
            await db.close()

    return get_db
