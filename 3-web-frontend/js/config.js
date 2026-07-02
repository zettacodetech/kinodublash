// Frontend konfiguratsiyasi. Backend manzilini shu yerda o'zgartiring.
window.APP_CONFIG = {
  // Markaziy FastAPI backend manzili (1-loyiha). Lokal Docker uchun localhost:8022.
  BACKEND_URL: "http://localhost:8022",
  // Status tekshirish oralig'i (ms)
  POLL_INTERVAL: 5000,
  // Maksimal yuklash hajmi (MB)
  MAX_UPLOAD_MB: 10240, // 10 GB (5 soatgacha video)
};
