import 'dart:async';

import 'package:dio/dio.dart';

import '../config.dart';

/// Task holati modeli.
class TaskStatus {
  final String status; // queued | processing | completed | failed
  final String stage;
  final int progress;
  final String? downloadUrl;
  final String? etaText;
  final String? error;

  TaskStatus({
    required this.status,
    required this.stage,
    required this.progress,
    this.downloadUrl,
    this.etaText,
    this.error,
  });

  factory TaskStatus.fromJson(Map<String, dynamic> json) => TaskStatus(
        status: json['status'] as String,
        stage: (json['stage'] ?? '') as String,
        progress: (json['progress'] ?? 0) as int,
        downloadUrl: json['download_url'] as String?,
        etaText: json['eta_text'] as String?,
        error: json['error'] as String?,
      );

  bool get isCompleted => status == 'completed';
  bool get isFailed => status == 'failed';
}

/// Backend API bilan aloqa (dio).
class ApiService {
  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: AppConfig.backendUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(minutes: 5),
    ),
  );

  /// Videoni /dub ga yuboradi. [onProgress] — yuklash foizi (0.0–1.0).
  /// Qaytadi: {task_id, eta_text, ...}
  Future<Map<String, dynamic>> submitDub({
    required String filePath,
    required String voice,
    String? externalId,
    void Function(double progress)? onProgress,
  }) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath, filename: 'video.mp4'),
      if (externalId != null) 'external_id': externalId,
    });

    final resp = await _dio.post(
      '/dub',
      queryParameters: {'voice': voice},
      data: formData,
      onSendProgress: (sent, total) {
        if (total > 0 && onProgress != null) onProgress(sent / total);
      },
    );
    return resp.data as Map<String, dynamic>;
  }

  /// YouTube (yoki boshqa) havolani /dub-url ga yuboradi.
  /// Qaytadi: {task_id, eta_text, ...}
  Future<Map<String, dynamic>> submitDubUrl({
    required String url,
    required String voice,
    String? externalId,
  }) async {
    final resp = await _dio.post(
      '/dub-url',
      data: {
        'url': url,
        'voice': voice,
        if (externalId != null) 'external_id': externalId,
      },
    );
    return resp.data as Map<String, dynamic>;
  }

  /// Bitta status so'rovi.
  Future<TaskStatus> getStatus(String taskId) async {
    final resp = await _dio.get('/status/$taskId');
    return TaskStatus.fromJson(resp.data as Map<String, dynamic>);
  }

  /// Tayyor bo'lguncha statusni Stream ko'rinishida qaytaradi.
  Stream<TaskStatus> pollStatus(String taskId) async* {
    final deadline = DateTime.now().add(AppConfig.pollTimeout);
    while (DateTime.now().isBefore(deadline)) {
      await Future.delayed(AppConfig.pollInterval);
      final status = await getStatus(taskId);
      yield status;
      if (status.isCompleted || status.isFailed) return;
    }
    throw TimeoutException('Render vaqti tugadi.');
  }

  /// Tayyor videoni lokal faylga yuklab oladi.
  Future<void> download(
    String taskId,
    String savePath, {
    void Function(double progress)? onProgress,
  }) async {
    await _dio.download(
      '/download/$taskId',
      savePath,
      onReceiveProgress: (received, total) {
        if (total > 0 && onProgress != null) onProgress(received / total);
      },
    );
  }
}
