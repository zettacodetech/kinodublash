/// Ilova konfiguratsiyasi. Backend manzilini shu yerda o'zgartiring.
class AppConfig {
  /// Markaziy FastAPI backend manzili (1-loyiha)
  static const String backendUrl = "https://api.sizning-domeningiz.uz";

  /// Status tekshirish oralig'i
  static const Duration pollInterval = Duration(seconds: 5);

  /// Maksimal kutish vaqti (5 soatlik videolar uzoq qayta ishlanadi)
  static const Duration pollTimeout = Duration(hours: 6);
}
