# 2-LOYIHA — Telegram Bot (Aiogram 3.x)

Alohida serverda ishlaydigan bot. **Hech qanday AI kaliti yo'q** — faqat markaziy backendga ulanadi.

## Ishlash mantig'i
1. Foydalanuvchi video yuboradi.
2. Bot Inline tugmalar orqali ovoz turini so'raydi (👨 Erkak / 👩 Ayol).
3. Videoni yuklab olib `httpx` orqali backendning `POST /dub` ga yuboradi.
4. Qaytgan `task_id` bo'yicha har 5 soniyada `GET /status/{id}` ni tekshiradi.
5. `completed` bo'lgach, tayyor videoni yuklab olib foydalanuvchiga qaytaradi.

## Struktura
```
2-telegram-bot/
├── bot/
│   ├── main.py        # Kirish nuqtasi (long polling)
│   ├── config.py      # .env sozlamalari (backend URL)
│   ├── handlers.py    # Video qabul qilish, status polling
│   ├── keyboards.py   # Inline tugmalar
│   └── api_client.py  # Backend bilan httpx aloqasi
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Ishga tushirish
```bash
cp .env.example .env       # BOT_TOKEN va BACKEND_URL ni to'ldiring
pip install -r requirements.txt
python -m bot.main
```

> **Eslatma:** Telegram Bot API oddiy botlar uchun ~50MB yuklashni cheklaydi.
> Kattaroq videolar uchun Web/Mobil ilovadan foydalaning.
