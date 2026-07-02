# 4-LOYIHA — Mobil ilova (Flutter / Dart)

Android/iOS mobil ilovaning manba kodi. Faqat markaziy backendga ulanadi.

## Xususiyatlar
- 🖼 `image_picker` — galereyadan video tanlash
- ⬆️ `dio` — yuklashda real vaqtdagi progress foizi (`onSendProgress`)
- ⏱ `Stream` (Timer) — backend statusini har 5 soniyada tekshirish
- ▶️ `video_player` — natijani ilova ichida ijro etish
- 💾 `gal` — tayyor videoni galereyaga saqlash

## Struktura
```
4-mobile-flutter/
├── lib/
│   ├── main.dart                    # App kirish nuqtasi (Dark theme)
│   ├── config.dart                  # backendUrl shu yerda
│   ├── services/api_service.dart    # dio: submitDub / pollStatus / download
│   ├── screens/home_screen.dart     # Asosiy UI + mantiq
│   └── widgets/voice_selector.dart  # Ovoz tanlash widgeti
├── android/app/src/main/AndroidManifest.xml
└── pubspec.yaml
```

## Sozlash
`lib/config.dart` faylida `backendUrl` ni o'z backend manzilingizga o'zgartiring.

## Ishga tushirish
```bash
flutter pub get
flutter run
```

## APK build qilish (Web-saytga joylash uchun)
```bash
flutter build apk --release
# Tayyor fayl:
#   build/app/outputs/flutter-apk/app-release.apk
# Uni 3-loyiha (web) downloads/ papkasiga ko'chiring:
cp build/app/outputs/flutter-apk/app-release.apk ../3-web-frontend/downloads/app-release.apk
```

> **Eslatma:** Agar backend HTTPS emas, HTTP (cleartext) ishlatsa,
> AndroidManifest.xml da `android:usesCleartextTraffic="true"` qiling.
