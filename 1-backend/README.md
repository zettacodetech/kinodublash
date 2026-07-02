# 1-LOYIHA — Markaziy Backend API (FastAPI)

Tizimning bosh miyasi. Videoni qabul qiladi, AI orqali tarjima + dublyaj qiladi va tayyor videoni qaytaradi. **Barcha AI kalitlari faqat shu yerda saqlanadi.**

## Struktura
```
1-backend/
├── app/
│   ├── main.py          # FastAPI endpointlar (/dub, /status, /download, /health)
│   ├── config.py        # .env sozlamalari (maxfiy kalitlar)
│   ├── database.py      # Async SQLAlchemy (PostgreSQL)
│   ├── models.py        # Users, Tasks jadvallari
│   ├── schemas.py       # Pydantic sxemalar
│   ├── crud.py          # DB operatsiyalari
│   ├── tasks.py         # Orqa fon render pipeline
│   ├── routers.py       # AI asboblar qutisi endpointlari (/ai/...)
│   └── services/
│       ├── ffmpeg_core.py # Audio ajratish, atempo time-stretch, mux
│       ├── engine.py      # Dispatcher: .env ga qarab provayder tanlaydi
│       ├── registry.py    # Barcha modellar katalogi (rol bo'yicha)
│       └── providers/
│           ├── stt/       # faster_whisper, openai_whisper, groq
│           ├── llm/       # ollama (llama/qwen/gemma...), groq
│           ├── tts/       # edge, openai, coqui, bark, chattts, melotts
│           ├── embeddings/# bge, nomic, MiniLM, mxbai
│           ├── image/     # SDXL, FLUX, PixArt, turbo (diffusers)
│           └── vision/    # LLaVA, moondream, qwen2-vl (ollama), BLIP
├── requirements.txt        # yengil: default provayderlar
├── requirements-local.txt  # og'ir: lokal modellar (torch, diffusers...)
├── nginx.conf.example      # 5GB yuklash uchun proxy
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Ko'p provayderli AI (multi-provider)
Har bir bosqichni `.env` orqali almashtirasiz — kodga tegmasdan:

| Rol | Provayderlar (`.env` kaliti) |
|-----|------------------------------|
| STT | `STT_PROVIDER` = `faster_whisper` \| `openai_whisper` \| `groq` |
| Tarjima | `TRANSLATION_PROVIDER` = `ollama` \| `groq` |
| TTS | `TTS_PROVIDER` = `edge` \| `openai` \| `coqui` \| `bark` \| `chattts` \| `melotts` |

**Default (bepul):** faster-whisper + Ollama + edge-tts (native o'zbek ovozi `uz-UZ-SardorNeural`/`uz-UZ-MadinaNeural`).

**Ovoz klonlash:** har odamning ovoziga o'xshatish uchun `TTS_PROVIDER=coqui` qiling va `requirements-local.txt` ni o'rnating. Pipeline har Whisper segmentidan qisqa `speaker_wav` reference kesib olib XTTS v2 ga beradi; Edge/OpenAI esa voice clone qilmaydi, faqat segment bo'yicha erkak/ayol ovoz tanlaydi.

### AI asboblar qutisi (qo'shimcha endpointlar)
| Method | Endpoint | Tavsif |
|--------|----------|--------|
| GET | `/ai/models` | Barcha ulangan modellar (rol bo'yicha) |
| POST | `/ai/translate` | Matnni o'zbekchaga tarjima |
| POST | `/ai/chat` | LLM suhbat |
| POST | `/ai/code` | Kod generatsiya (coder modellari) |
| POST | `/ai/tts` | Matndan audio |
| POST | `/ai/embed` | Matn embeddinglari |
| POST | `/ai/image` | Matndan rasm (SDXL/FLUX) |
| POST | `/ai/vision` | Rasmni tavsiflash (LLaVA) |
| POST | `/ai/caption` | Rasmga izoh (BLIP) |

### Ollama va lokal modellar
```bash
# Ollama o'rnatib, kerakli modellarni torting:
ollama pull qwen2.5:7b          # tarjima
ollama pull qwen2.5-coder:7b    # kod
ollama pull llava:13b           # vision

# Og'ir lokal modellar (embeddings, rasm-gen, boshqa TTS):
pip install -r requirements-local.txt

# Original speaker ovoziga yaqin dublyaj uchun:
# .env -> TTS_PROVIDER=coqui
```

## Ishga tushirish (lokal)
```bash
cp .env.example .env         # kalitlarni to'ldiring
# FFmpeg o'rnatilgan bo'lishi shart:  sudo apt install ffmpeg
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker orqali (PostgreSQL bilan birga)
```bash
cp .env.example .env
docker compose up --build
```

## API
| Method | Endpoint | Tavsif |
|--------|----------|--------|
| POST | `/dub?voice=male\|female` | Video yuklaydi, `task_id` qaytaradi, renderni orqa fonda boshlaydi |
| GET | `/status/{task_id}` | `queued/processing/completed/failed`, progress, download_url |
| GET | `/download/{task_id}` | Tayyor videoni fayl sifatida qaytaradi |
| GET | `/health` | Servis holati |

Swagger hujjatlari: `http://localhost:8000/docs`
