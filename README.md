# 🎬 AI Video Dublyaj Tizimi (Mikroxizmatlar)

Sun'iy intellekt yordamida videolarni chet tilidan **o'zbek tiliga** avtomatik tarjima qilib, ovozlashtiruvchi (dublyaj) **production-ready** tizim.

Tizim 4 ta **mutlaqo alohida** loyihadan (repository) iborat. Barcha platformalar markaziy Backend API orqali gaplashadi. **AI API kalitlari faqat backendda yashirin turadi.**

```
                        ┌─────────────────────┐
                        │   2. TELEGRAM BOT   │
                        │     (Aiogram 3.x)   │
                        └──────────┬──────────┘
                                   │ httpx
┌────────────────────┐            │            ┌────────────────────┐
│  3. WEB FRONTEND   │───────┐    │    ┌───────│  4. FLUTTER MOBIL  │
│  (HTML/Tailwind)   │ fetch │    │    │  dio  │      (Dart)        │
└────────────────────┘       ▼    ▼    ▼       └────────────────────┘
                        ┌─────────────────────────┐
                        │   1. MARKAZIY BACKEND   │
                        │        (FastAPI)        │
                        │  ┌───────────────────┐  │
                        │  │ Groq (STT+Tarjima)│  │
                        │  │ OpenAI TTS        │  │  ← API kalitlar shu yerda
                        │  │ FFmpeg (dublyaj)  │  │
                        │  └───────────────────┘  │
                        │      PostgreSQL         │
                        └─────────────────────────┘
```

## Loyihalar

| # | Loyiha | Texnologiya | Papka |
|---|--------|-------------|-------|
| 1 | Markaziy Backend API | FastAPI + PostgreSQL + FFmpeg | [`1-backend/`](./1-backend) |
| 2 | Telegram Bot | Aiogram 3.x + httpx | [`2-telegram-bot/`](./2-telegram-bot) |
| 3 | Web Frontend | HTML + Tailwind + JS | [`3-web-frontend/`](./3-web-frontend) |
| 4 | Mobil ilova | Flutter / Dart | [`4-mobile-flutter/`](./4-mobile-flutter) |

## Dublyaj pipeline'i (backend)
1. 🎧 Videodan audio ajratish (FFmpeg)
2. 📝 Nutqni vaqtli segmentlarga ajratib matnga o'girish (Whisper/Groq)
3. 🌐 Matnni o'zbekchaga tarjima (Groq Llama 3)
4. 🔊 Har gap segmenti uchun ovoz generatsiyasi:
   - `TTS_PROVIDER=coqui` bo'lsa, original segmentdan `speaker_wav` olinib XTTS voice clone qilinadi
   - boshqa TTS providerlarda segment jinsiga qarab erkak/ayol ovozi tanlanadi
5. ⏱ Har segment audio vaqtini original segmentga moslash (FFmpeg `atempo` time-stretch)
6. 🎬 Yangi audioni videoga yopishtirish (FFmpeg mux)

## Ishga tushirish tartibi
1. **Backend** ni ishga tushiring (kalitlarni `.env` ga yozing) — `1-backend/README.md`
2. Har bir mijoz loyihada backend manzilini sozlang:
   - Bot: `2-telegram-bot/.env` → `BACKEND_URL`
   - Web: `3-web-frontend/js/config.js` → `BACKEND_URL`
   - Mobil: `4-mobile-flutter/lib/config.dart` → `backendUrl`
3. Flutter'dan APK build qilib, `3-web-frontend/downloads/` ga joylang.

## Talablar
- Backend: Python 3.12+, **FFmpeg**, PostgreSQL 14+, Groq & OpenAI kalitlari
- Bot: Python 3.12+, Telegram bot tokeni
- Web: har qanday statik hosting (Vercel/Nginx)
- Mobil: Flutter SDK 3.3+
