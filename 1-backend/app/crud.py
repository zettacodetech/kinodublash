"""Ma'lumotlar bazasi bilan ishlash funksiyalari (async)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Task, TaskStatus, User, VoiceType


async def get_or_create_user(
    db: AsyncSession,
    external_id: str | None,
    username: str | None = None,
    full_name: str | None = None,
) -> User | None:
    if not external_id:
        return None
    result = await db.execute(select(User).where(User.external_id == external_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(external_id=external_id, username=username, full_name=full_name)
        db.add(user)
        await db.flush()
    return user


async def create_task(
    db: AsyncSession,
    task_id: str,
    voice: VoiceType,
    source_path: str,
    file_size: int,
    user_id: int | None = None,
    duration_seconds: float | None = None,
    eta_seconds: int | None = None,
) -> Task:
    task = Task(
        id=task_id,
        voice=voice,
        source_path=source_path,
        file_size=file_size,
        user_id=user_id,
        duration_seconds=duration_seconds,
        eta_seconds=eta_seconds,
        status=TaskStatus.QUEUED,
        stage="queued",
        progress=0,
    )
    db.add(task)
    await db.flush()
    return task


async def get_task(db: AsyncSession, task_id: str) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def update_task(db: AsyncSession, task_id: str, **fields) -> None:
    task = await get_task(db, task_id)
    if task is None:
        return
    for key, value in fields.items():
        setattr(task, key, value)
    await db.commit()
