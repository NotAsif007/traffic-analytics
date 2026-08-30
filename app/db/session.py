"""
Async SQLAlchemy engine and session factory.

The engine is created once at application startup and shared across all requests.
Each request gets its own AsyncSession via get_db() dependency injection.

Never import the engine directly in business logic — always go through
the session provided by dependency injection.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings

# Module-level references, initialised by init_db()
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> None:
    """
    Initialise the async engine and session factory.

    Called once from the application lifespan. Idempotent — safe to call
    multiple times in tests.
    """
    global _engine, _async_session_factory

    _engine = create_async_engine(
        str(settings.DATABASE_URL),
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        # Echo SQL only in debug mode — never in production
        echo=settings.DEBUG and not settings.is_production,
        # Use NullPool for test environments if needed (set via override)
    )

    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


def get_engine() -> AsyncEngine:
    """Return the shared async engine. Raises if init_db() was not called."""
    if _engine is None:
        raise RuntimeError("Database engine not initialised. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory. Raises if init_db() was not called."""
    if _async_session_factory is None:
        raise RuntimeError("Session factory not initialised. Call init_db() first.")
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession per request.

    The session is committed on success and rolled back on any exception.
    Always closed at the end of the request.

    Usage:
        async def my_route(db: AsyncSession = Depends(get_db)): ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """
    Dispose the engine connection pool.

    Called from the application lifespan shutdown handler.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
