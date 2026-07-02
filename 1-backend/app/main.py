"""
Markaziy Backend API — tizimning bosh miyasi.
Endpointlar: POST /dub, GET /status/{id}, GET /download/{id}, GET /health.
"""
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, eta as eta_util
from .config import settings
from .database import get_db, init_db
from .models import TaskStatus, VoiceType
from .services import ffmpeg_core, youtube
from .routers import router as ai_router
from .schemas import DubUrlRequest, HealthResponse, TaskCreateResponse, TaskStatusResponse
from .tasks import process_dubbing, process_dubbing_from_url

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    settings.prepare_dirs()
    yield


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

# Tashqi ilovalar (bot, web, mobil) xatosiz ulanishi uchun CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI asboblar qutisi endpointlari (/ai/...)
app.include_router(ai_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        app=settings.APP_NAME,
        voices={"male": settings.TTS_VOICE_MALE, "female": settings.TTS_VOICE_FEMALE},
    )


@app.post("/dub", response_model=TaskCreateResponse, status_code=202)
async def create_dub(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Tarjima qilinadigan video"),
    voice: VoiceType = Query(VoiceType.AUTO, description="auto | male | female"),
    external_id: str | None = Form(None, description="Mijoz identifikatori (ixtiyoriy)"),
    username: str | None = Form(None),
    full_name: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> TaskCreateResponse:
    """Videoni qabul qiladi, task yaratadi va renderni orqa fonda boshlaydi."""
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Faqat video fayl qabul qilinadi.")

    user = await crud.get_or_create_user(db, external_id, username, full_name)

    # Faylni diskka oqim orqali saqlaymiz (katta fayllar uchun xotira tejaladi).
    task_id = uuid.uuid4().hex
    ext = Path(file.filename or "video.mp4").suffix or ".mp4"
    source_path = settings.upload_dir / f"{task_id}{ext}"

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    size = 0
    with source_path.open("wb") as out:
        while chunk := await file.read(4 * 1024 * 1024):  # 4MB bo'laklar (katta fayllarga tez)
            size += len(chunk)
            if size > max_bytes:
                out.close()
                source_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"Fayl {settings.MAX_UPLOAD_MB}MB dan katta.")
            out.write(chunk)

    # Davomiylikni o'lchab, taxminiy ishlov vaqtini (ETA) hisoblaymiz
    try:
        duration = await ffmpeg_core.get_duration(source_path)
    except Exception:  # noqa: BLE001
        duration = None
    eta_sec = eta_util.estimate_seconds(duration)

    await crud.create_task(
        db,
        task_id=task_id,
        voice=voice,
        source_path=str(source_path),
        file_size=size,
        user_id=user.id if user else None,
        duration_seconds=duration,
        eta_seconds=eta_sec,
    )
    await db.commit()

    background_tasks.add_task(process_dubbing, task_id, str(source_path), voice)
    return TaskCreateResponse(
        task_id=task_id, status=TaskStatus.QUEUED,
        duration_seconds=duration, eta_seconds=eta_sec, eta_text=eta_util.format_uz(eta_sec),
    )


@app.post("/dub-url", response_model=TaskCreateResponse, status_code=202)
async def create_dub_url(
    body: DubUrlRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> TaskCreateResponse:
    """YouTube (yoki boshqa) havolani qabul qiladi, videoni o'zi yuklab olib dublyaj qiladi."""
    if not body.url.strip().lower().startswith("http"):
        raise HTTPException(status_code=400, detail="Yaroqli havola (URL) yuboring.")

    user = await crud.get_or_create_user(db, body.external_id, body.username, body.full_name)

    task_id = uuid.uuid4().hex
    source_path = settings.upload_dir / f"{task_id}.mp4"

    # Havoladan davomiylikni metadata orqali olib ETA hisoblaymiz (yuklab olmasdan)
    duration = await youtube.get_duration(body.url)
    eta_sec = eta_util.estimate_seconds(duration)

    await crud.create_task(
        db,
        task_id=task_id,
        voice=body.voice,
        source_path=str(source_path),
        file_size=0,
        user_id=user.id if user else None,
        duration_seconds=duration,
        eta_seconds=eta_sec,
    )
    await db.commit()

    background_tasks.add_task(process_dubbing_from_url, task_id, body.url, str(source_path), body.voice)
    return TaskCreateResponse(
        task_id=task_id, status=TaskStatus.QUEUED,
        duration_seconds=duration, eta_seconds=eta_sec, eta_text=eta_util.format_uz(eta_sec),
    )


@app.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_status(task_id: str, db: AsyncSession = Depends(get_db)) -> TaskStatusResponse:
    """Render holatini bazadan tekshiradi. Tayyor bo'lsa download_url beradi."""
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task topilmadi.")

    download_url = None
    if task.status == TaskStatus.COMPLETED:
        download_url = f"{settings.BASE_URL.rstrip('/')}/download/{task_id}"

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        stage=task.stage,
        progress=task.progress,
        duration_seconds=task.duration_seconds,
        eta_seconds=task.eta_seconds,
        eta_text=eta_util.format_uz(task.eta_seconds),
        download_url=download_url,
        error=task.error,
        created_at=task.created_at,
    )


@app.get("/download/{task_id}")
async def download(task_id: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    """Tayyor videoni fayl sifatida qaytaradi."""
    task = await crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task topilmadi.")
    if task.status != TaskStatus.COMPLETED or not task.output_path:
        raise HTTPException(status_code=409, detail="Video hali tayyor emas.")

    path = Path(task.output_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Fayl serverdan o'chirilgan.")

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"dubbed_{task_id}.mp4",
    )
