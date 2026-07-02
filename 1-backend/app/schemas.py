"""Pydantic sxemalari (request/response validatsiyasi)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .models import TaskStatus, VoiceType


class TaskCreateResponse(BaseModel):
    task_id: str
    status: TaskStatus
    duration_seconds: float | None = None
    eta_seconds: int | None = None
    eta_text: str | None = None
    message: str = "Buyurtma qabul qilindi. Render orqa fonda boshlandi."


class DubUrlRequest(BaseModel):
    url: str
    voice: VoiceType = VoiceType.AUTO
    external_id: str | None = None
    username: str | None = None
    full_name: str | None = None


class TaskStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    status: TaskStatus
    stage: str
    progress: int
    duration_seconds: float | None = None
    eta_seconds: int | None = None
    eta_text: str | None = None
    download_url: str | None = None
    error: str | None = None
    created_at: datetime | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str | None
    username: str | None
    full_name: str | None


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    voices: dict[str, str]
