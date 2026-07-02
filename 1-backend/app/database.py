"""Asinxron SQLAlchemy ulanishi va sessiya boshqaruvi."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Barcha modellar uchun bazaviy klass."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: har bir request uchun sessiya."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Ishga tushishda jadvallarni yaratadi (ishlab chiqarishda Alembic tavsiya etiladi)."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Mavjud bazaga yangi ustunlarni xavfsiz qo'shish (nusxa buzilmasin)
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS duration_seconds DOUBLE PRECISION"))
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS eta_seconds INTEGER"))
