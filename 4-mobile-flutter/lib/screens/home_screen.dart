import 'dart:io';

import 'package:flutter/material.dart';
import 'package:gal/gal.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:video_player/video_player.dart';

import '../services/api_service.dart';
import '../widgets/voice_selector.dart';

enum AppStage { idle, uploading, processing, completed, error }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiService _api = ApiService();
  final ImagePicker _picker = ImagePicker();

  AppStage _stage = AppStage.idle;
  String _voice = 'auto';
  File? _pickedVideo;
  final TextEditingController _urlController = TextEditingController();

  double _uploadProgress = 0;
  int _renderProgress = 0;
  String _stageLabel = '';
  String? _eta;
  String _error = '';

  String? _savedPath; // yuklab olingan tayyor video
  VideoPlayerController? _videoController;

  static const _stageLabels = {
    'queued': '⏳ Navbatda...',
    'download': '⬇️ Havoladan yuklab olinmoqda...',
    'voice_detect': '🕵️ Ovoz turi aniqlanmoqda...',
    'audio_extract': '🎧 Audio ajratilmoqda...',
    'transcribe': '📝 Nutq matnga o\'girilmoqda...',
    'translate': '🌐 AI tarjima qilmoqda...',
    'tts': '🔊 Ovoz generatsiya qilinmoqda...',
    'time_stretch': '⏱ Vaqt moslashtirilmoqda...',
    'mux': '🎬 Video yig\'ilmoqda...',
    'completed': '✅ Tayyor!',
  };

  @override
  void dispose() {
    _videoController?.dispose();
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _pickVideo() async {
    final XFile? picked = await _picker.pickVideo(source: ImageSource.gallery);
    if (picked != null) {
      setState(() {
        _pickedVideo = File(picked.path);
        _stage = AppStage.idle;
        _error = '';
      });
    }
  }

  Future<void> _startDubbing() async {
    final url = _urlController.text.trim();
    if (_pickedVideo == null && url.isEmpty) return;

    setState(() {
      _stage = url.isNotEmpty ? AppStage.processing : AppStage.uploading;
      _uploadProgress = 0;
      _renderProgress = 0;
      _error = '';
    });

    try {
      final Map<String, dynamic> res;
      if (url.isNotEmpty) {
        // Havola — backend o'zi yuklab oladi (upload progress yo'q)
        res = await _api.submitDubUrl(url: url, voice: _voice);
      } else {
        // Fayl — yuklash progressi bilan
        res = await _api.submitDub(
          filePath: _pickedVideo!.path,
          voice: _voice,
          onProgress: (p) => setState(() => _uploadProgress = p),
        );
      }
      final taskId = res['task_id'] as String;
      setState(() => _eta = res['eta_text'] as String?);

      // Render statusini kuzatish
      setState(() {
        _stage = AppStage.processing;
        _renderProgress = 0;
      });
      await for (final status in _api.pollStatus(taskId)) {
        if (!mounted) return;
        setState(() {
          _renderProgress = status.progress;
          _stageLabel = _stageLabels[status.stage] ?? '⚙️ Ishlanmoqda...';
          if (status.etaText != null) _eta = status.etaText;
        });
        if (status.isFailed) {
          throw Exception(status.error ?? 'Render xatoligi');
        }
        if (status.isCompleted) break;
      }

      // 3) Tayyor videoni yuklab olish
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/dubbed_$taskId.mp4';
      await _api.download(taskId, path);

      // 4) Pleyerni tayyorlash
      final controller = VideoPlayerController.file(File(path));
      await controller.initialize();
      if (!mounted) return;
      setState(() {
        _savedPath = path;
        _videoController = controller;
        _stage = AppStage.completed;
      });
      controller.play();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _stage = AppStage.error;
        _error = e.toString();
      });
    }
  }

  Future<void> _saveToGallery() async {
    if (_savedPath == null) return;
    try {
      await Gal.putVideo(_savedPath!);
      _snack('✅ Video galereyaga saqlandi.');
    } catch (e) {
      _snack('❌ Saqlashda xatolik: $e');
    }
  }

  void _reset() {
    _videoController?.dispose();
    _urlController.clear();
    setState(() {
      _stage = AppStage.idle;
      _pickedVideo = null;
      _eta = null;
      _savedPath = null;
      _videoController = null;
      _uploadProgress = 0;
      _renderProgress = 0;
    });
  }

  void _snack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Video Dublyaj'),
        centerTitle: true,
        backgroundColor: Colors.transparent,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: _buildBody(),
        ),
      ),
    );
  }

  Widget _buildBody() {
    switch (_stage) {
      case AppStage.uploading:
        return _progressView(
          'Serverga yuklanmoqda...',
          _uploadProgress,
          '${(_uploadProgress * 100).toStringAsFixed(0)}%',
        );
      case AppStage.processing:
        return _progressView(_stageLabel, _renderProgress / 100, '$_renderProgress%');
      case AppStage.completed:
        return _resultView();
      case AppStage.error:
        return _errorView();
      case AppStage.idle:
        return _idleView();
    }
  }

  // ---------- Ko'rinishlar ----------
  Widget _idleView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        GestureDetector(
          onTap: _pickVideo,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 48),
            decoration: BoxDecoration(
              color: const Color(0xFF1F2937),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF374151)),
            ),
            child: Column(
              children: [
                Icon(
                  _pickedVideo == null ? Icons.video_library_outlined : Icons.check_circle,
                  size: 48,
                  color: _pickedVideo == null
                      ? Colors.grey
                      : Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(height: 12),
                Text(
                  _pickedVideo == null
                      ? 'Video tanlash uchun bosing'
                      : 'Video tanlandi ✓',
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Row(children: [
          const Expanded(child: Divider(color: Color(0xFF374151))),
          const Padding(padding: EdgeInsets.symmetric(horizontal: 8), child: Text('yoki', style: TextStyle(color: Colors.grey))),
          const Expanded(child: Divider(color: Color(0xFF374151))),
        ]),
        const SizedBox(height: 12),
        TextField(
          controller: _urlController,
          onChanged: (_) => setState(() {}),
          keyboardType: TextInputType.url,
          decoration: InputDecoration(
            hintText: '🔗 YouTube havolasini joylang (kino/serial)...',
            filled: true,
            fillColor: const Color(0xFF111827),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          ),
        ),
        const SizedBox(height: 24),
        const Text('Dublyaj ovozi:', style: TextStyle(fontWeight: FontWeight.w500)),
        const SizedBox(height: 12),
        VoiceSelector(value: _voice, onChanged: (v) => setState(() => _voice = v)),
        const SizedBox(height: 8),
        const Text('🤖 Avtomatik — videodagi ovozga qarab tanlanadi.',
            style: TextStyle(color: Colors.grey, fontSize: 12)),
        const Spacer(),
        FilledButton(
          onPressed: (_pickedVideo == null && _urlController.text.trim().isEmpty)
              ? null
              : _startDubbing,
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
          child: const Text('🚀 Dublyajni boshlash', style: TextStyle(fontSize: 16)),
        ),
      ],
    );
  }

  Widget _progressView(String label, double value, String percent) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 120,
            height: 120,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 120,
                  height: 120,
                  child: CircularProgressIndicator(
                    value: value > 0 ? value : null,
                    strokeWidth: 8,
                    backgroundColor: const Color(0xFF374151),
                  ),
                ),
                Text(percent, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
          const SizedBox(height: 8),
          if (_eta != null)
            Text('⏱ Taxminiy vaqt: $_eta',
                style: TextStyle(color: Theme.of(context).colorScheme.primary, fontWeight: FontWeight.w500)),
          const SizedBox(height: 4),
          const Text('Iltimos kuting...', style: TextStyle(color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _resultView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('✅ Tayyor!',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        if (_videoController != null && _videoController!.value.isInitialized)
          AspectRatio(
            aspectRatio: _videoController!.value.aspectRatio,
            child: Stack(
              alignment: Alignment.center,
              children: [
                VideoPlayer(_videoController!),
                IconButton(
                  iconSize: 56,
                  icon: Icon(
                    _videoController!.value.isPlaying
                        ? Icons.pause_circle
                        : Icons.play_circle,
                    color: Colors.white70,
                  ),
                  onPressed: () => setState(() {
                    _videoController!.value.isPlaying
                        ? _videoController!.pause()
                        : _videoController!.play();
                  }),
                ),
              ],
            ),
          ),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: _saveToGallery,
                icon: const Icon(Icons.download),
                label: const Text('Galereyaga saqlash'),
                style: FilledButton.styleFrom(
                  backgroundColor: Colors.green.shade600,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _reset,
                icon: const Icon(Icons.refresh),
                label: const Text('Yangi video'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _errorView() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 56, color: Colors.redAccent),
          const SizedBox(height: 16),
          const Text('Xatolik yuz berdi', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(_error, textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey)),
          const SizedBox(height: 24),
          FilledButton(onPressed: _reset, child: const Text('Qaytadan urinish')),
        ],
      ),
    );
  }
}
