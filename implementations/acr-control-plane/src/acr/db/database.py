from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from acr.config import settings


class Base(DeclarativeBase):
    pass


# ── Two-pool design ─────────────────────────────────────────────────────────
# Hot-path pool: serves /acr/evaluate and other latency-sensitive endpoints.
# Background pool: serves telemetry persistence, drift sampling, and drift
# checks that run in FastAPI BackgroundTasks.  Separating the pools prevents
# background work from starving request-handling connections under load
# (~100 req/s was enough to exhaust the old shared pool of 30).

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=25,
    max_overflow=25,  # 50 total for hot path
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Background task pool — smaller, isolated from the hot path.
background_engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=10,  # 20 total for background tasks
    pool_pre_ping=True,
)

BackgroundSessionLocal = async_sessionmaker(
    bind=background_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
