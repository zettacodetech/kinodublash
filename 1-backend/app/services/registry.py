"""
Barcha AI modellarining markaziy katalogi — ROL bo'yicha guruhlangan.
GET /ai/models endpointi shu ma'lumotni qaytaradi. Bu tizimga qanday
modellar ulanganini bir joyda ko'rsatadi.
"""

MODEL_REGISTRY: dict[str, dict] = {
    # ================= NUTQ -> MATN (STT) =================
    "stt": {
        "description": "Audio/video nutqini matnga o'giradi",
        "providers": {
            "faster_whisper": ["large-v3", "medium", "small", "base"],
            "openai_whisper": ["large-v3", "medium", "small", "base"],
            "groq": ["whisper-large-v3"],
        },
    },
    # ================= LLM / TARJIMA =================
    "llm": {
        "description": "Matnni tarjima qiladi va suhbat / matn generatsiya qiladi",
        "providers": {
            "ollama": [
                "llama3.2:1b", "llama3.2:3b", "llama3.1:8b",
                "qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b",
                "gemma2:2b", "gemma2:9b", "phi3.5:mini", "phi3:medium",
                "mistral:7b", "hermes3:8b", "solar:10.7b", "yi:9b",
                "stablelm-zephyr:3b", "openchat", "orca2",
            ],
            "groq": ["llama-3.3-70b-versatile"],
        },
    },
    # ================= KOD MODELLARI =================
    "code": {
        "description": "Dasturiy kod generatsiya va tahlil",
        "providers": {
            "ollama": [
                "codellama:7b", "codellama:13b",
                "qwen2.5-coder:1.5b", "qwen2.5-coder:7b",
                "deepseek-coder:1.3b", "deepseek-coder:6.7b",
                "codegemma:2b", "codegemma:7b",
            ],
        },
    },
    # ================= MATN -> NUTQ (TTS) =================
    "tts": {
        "description": "Matndan ovozli audio yaratadi",
        "providers": {
            "edge": ["uz-UZ-SardorNeural", "uz-UZ-MadinaNeural"],  # native o'zbek!
            "openai": ["onyx", "nova", "alloy", "echo", "fable", "shimmer"],
            "coqui": ["xtts_v2"],
            "bark": ["suno/bark"],
            "chattts": ["ChatTTS"],
            "melotts": ["MeloTTS"],
        },
    },
    # ================= EMBEDDINGS =================
    "embeddings": {
        "description": "Matnni vektorga aylantiradi (qidiruv/RAG uchun)",
        "providers": {
            "sentence_transformers": [
                "BAAI/bge-large-en-v1.5",
                "nomic-ai/nomic-embed-text-v1.5",
                "sentence-transformers/all-MiniLM-L6-v2",
                "mixedbread-ai/mxbai-embed-large-v1",
            ],
        },
    },
    # ================= RASM GENERATSIYA =================
    "image": {
        "description": "Matndan rasm yaratadi (diffusers)",
        "providers": {
            "diffusers": [
                "stabilityai/stable-diffusion-xl-base-1.0",
                "stabilityai/sdxl-turbo",
                "black-forest-labs/FLUX.1-schnell",
                "black-forest-labs/FLUX.1-dev",
                "latent-consistency/lcm-sdxl",
                "PixArt-alpha/PixArt-XL-2-1024x1024",
                "Prompthero/openjourney",
            ],
        },
    },
    # ================= VISION (RASMNI TUSHUNISH) =================
    "vision": {
        "description": "Rasmni tavsiflaydi va savollarga javob beradi",
        "providers": {
            "ollama": ["llava:7b", "llava:13b", "moondream", "qwen2-vl"],
            "transformers": [
                "google/paligemma-3b-pt-448",
                "openbmb/MiniCPM-V-2_6",
                "Salesforce/blip-image-captioning-large",
            ],
        },
    },
}


def list_models() -> dict:
    return MODEL_REGISTRY
