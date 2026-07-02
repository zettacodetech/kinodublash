# 3-LOYIHA — Web Frontend (HTML + Tailwind + JS)

Statik veb-sayt. Vercel yoki Nginx'da turadi, Telegram Web App (TWA) ichida ham ishlaydi.

## Xususiyatlar
- 🌙 Qorong'u (Dark Mode) korporativ dizayn
- 📥 Drag & Drop video yuklash
- 🎙 Custom Radio ovoz tanlash (Erkak/Ayol)
- ⭕ Animatsiyali halqali Progress Bar (Yuklanmoqda → AI tarjima → Tayyor)
- ▶️ HTML5 `<video>` pleyerda natija + yuklab olish tugmasi
- 📱 `downloads/app-release.apk` uchun "APK yuklash" tugmasi
- 🤝 Telegram Web App SDK integratsiyasi (foydalanuvchi ma'lumotini uzatadi)

## Struktura
```
3-web-frontend/
├── index.html
├── css/style.css
├── js/
│   ├── config.js     # BACKEND_URL shu yerda
│   └── app.js        # Fetch API mantiqi
├── downloads/
│   └── app-release.apk   # (4-loyihadan build qilinadi)
└── vercel.json
```

## Sozlash
`js/config.js` faylida `BACKEND_URL` ni o'z backend manzilingizga o'zgartiring.

## Ishga tushirish (lokal)
```bash
python3 -m http.server 3000
# so'ng brauzerda:  http://localhost:3000
```

## Deploy (Vercel)
```bash
npm i -g vercel
vercel --prod
```
