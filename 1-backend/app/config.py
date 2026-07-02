"""Ilova sozlamalari. Barcha maxfiy kalitlar faqat shu yerda (backendda) yashiringan."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Umumiy ---
    APP_NAME: str = "AI Video Dublyaj Backend"
    DEBUG: bool = False
    BASE_URL: str = "http://localhost:8000"  # /download link generatsiya qilish uchun

    # --- Ma'lumotlar bazasi (PostgreSQL, async) ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dubbing"

    # === Dublyaj pipeline uchun provayder tanlovi (.env dan almashtiriladi) ===
    STT_PROVIDER: str = "faster_whisper"    # faster_whisper | openai_whisper | groq
    TRANSLATION_PROVIDER: str = "ollama"    # ollama | groq
    TTS_PROVIDER: str = "edge"              # edge | openai | coqui | bark | chattts | melotts

    # === Bulut kalitlari (MAXFIY) ===
    GROQ_API_KEY: str = ""
    GROQ_API_KEYS: str = ""  # vergul bilan ajratilgan bir nechta Groq key; GROQ_API_KEY fallback bo'lib qoladi
    OPENAI_API_KEY: str = ""

    # --- Groq modellari ---
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"
    GROQ_LLM_MODEL: str = "llama-3.3-70b-versatile"

    # --- OpenAI TTS ---
    OPENAI_TTS_MODEL: str = "tts-1"
    TTS_VOICE_MALE: str = "onyx"
    TTS_VOICE_FEMALE: str = "nova"

    # === Ollama (lokal LLM/vision/kod) ===
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen2.5:7b"          # tarjima uchun
    OLLAMA_CODE_MODEL: str = "qwen2.5-coder:7b"   # kod uchun
    OLLAMA_VISION_MODEL: str = "llava:13b"        # rasmni tavsiflash uchun
    OLLAMA_TRANSLATE_TIMEOUT_SECONDS: float = 20.0

    # === Lokal Whisper (faster-whisper / openai-whisper) ===
    WHISPER_MODEL_SIZE: str = "large-v3"          # large-v3 | medium | small | base
    WHISPER_DEVICE: str = "auto"                  # cpu | cuda | auto
    WHISPER_COMPUTE_TYPE: str = "int8"            # int8 | float16 | float32

    # === Edge-TTS (BEPUL, native o'zbek ovozlari) ===
    EDGE_TTS_VOICE_MALE: str = "uz-UZ-SardorNeural"
    EDGE_TTS_VOICE_FEMALE: str = "uz-UZ-MadinaNeural"

    # === Boshqa lokal TTS ===
    COQUI_TTS_MODEL: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    COQUI_TTS_LANGUAGE: str = "tr"  # XTTS uzbekni bevosita qo'llamaydi; turkiy yaqin fallback
    MELO_TTS_LANGUAGE: str = "EN"

    # === Speaker-aware dublyaj ===
    SPEAKER_REFERENCE_SECONDS: float = 8.0
    SPEAKER_REFERENCE_PAD_SECONDS: float = 0.25
    MIN_SPEECH_SEGMENT_SECONDS: float = 0.35

    # Ovoz tezligi AVTOMATIK — har segment odam gapirish tempiga moslanadi.
    # MAX_TTS_SPEEDUP = eng ko'p tezlashtirish (sinxron uchun), MIN_TTS_SLOWDOWN = eng ko'p sekinlashtirish.
    MAX_TTS_SPEEDUP: float = 2.0
    MIN_TTS_SLOWDOWN: float = 0.9

    # === Embeddings ===
    EMBEDDING_MODEL: str = "./models/bge-large"   # lokal papka yoki HF id

    # === Rasm generatsiya (diffusers) ===
    IMAGE_MODEL: str = "./models/sdxl-turbo"
    IMAGE_DEVICE: str = "cuda"                     # cuda | cpu | mps

    # === Vision (rasm tavsifi) ===
    BLIP_MODEL: str = "./models/blip"

    # --- YouTube (yt-dlp) ---
    YT_DLP_PLAYER_CLIENT: str = "android"             # 429/throttling ni yumshatadi
    YT_DLP_COOKIES: str = "/app/storage/cookies.txt"  # bot-tekshiruvni chetlash (ixtiyoriy)

    # --- Uzun video (chunking) ---
    SEGMENT_SECONDS: int = 480   # audioni 8 daqiqalik bo'laklarga bo'ladi (Groq 25MB limiti + sync)
    # Bir vaqtda parallel qayta ishlanadigan segmentlar soni (tezlashtirish).
    # Groq(4 kalit)+edge tarmoq I/O bo'lgani uchun parallellik katta tezlik beradi.
    SEGMENT_CONCURRENCY: int = 5

    # --- ETA (taxminiy ishlov vaqti) ---
    # ishlov_vaqti ≈ video_davomiyligi * ETA_FACTOR + ETA_BASE_SECONDS
    # CPU + Groq + edge-tts uchun ~0.6. GPU (faster-whisper) da kamayadi.
    ETA_FACTOR: float = 0.6
    ETA_BASE_SECONDS: int = 45

    # --- Fayl saqlash ---
    STORAGE_DIR: Path = Path("storage")
    MAX_UPLOAD_MB: int = 10240   # 10 GB (5 soatlik videolar uchun)

    @property
    def groq_api_keys(self) -> list[str]:
        keys: list[str] = []
        raw_keys = [part.strip() for part in self.GROQ_API_KEYS.replace("\n", ",").split(",")]
        for key in [*raw_keys, self.GROQ_API_KEY.strip()]:
            if key and key not in keys:
                keys.append(key)
        return keys

    @property
    def upload_dir(self) -> Path:
        return self.STORAGE_DIR / "uploads"

    @property
    def output_dir(self) -> Path:
        return self.STORAGE_DIR / "outputs"

    @property
    def temp_dir(self) -> Path:
        return self.STORAGE_DIR / "temp"

    def prepare_dirs(self) -> None:
        for d in (self.upload_dir, self.output_dir, self.temp_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.prepare_dirs()
    return settings


settings = get_settings()
