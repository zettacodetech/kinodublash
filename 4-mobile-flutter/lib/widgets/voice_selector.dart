import 'package:flutter/material.dart';

/// Erkak/Ayol ovoz tanlash widgeti.
class VoiceSelector extends StatelessWidget {
  final String value; // 'male' | 'female'
  final ValueChanged<String> onChanged;

  const VoiceSelector({super.key, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _option(context, 'auto', '🤖', 'Avtomatik'),
        const SizedBox(width: 10),
        _option(context, 'male', '👨', 'Erkak'),
        const SizedBox(width: 10),
        _option(context, 'female', '👩', 'Ayol'),
      ],
    );
  }

  Widget _option(BuildContext context, String key, String emoji, String label) {
    final selected = value == key;
    final brand = Theme.of(context).colorScheme.primary;
    return Expanded(
      child: GestureDetector(
        onTap: () => onChanged(key),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 16),
          decoration: BoxDecoration(
            color: selected ? brand.withOpacity(0.12) : const Color(0xFF1F2937),
            border: Border.all(
              color: selected ? brand : const Color(0xFF374151),
              width: 1.5,
            ),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            children: [
              Text(emoji, style: const TextStyle(fontSize: 24)),
              const SizedBox(height: 4),
              Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
            ],
          ),
        ),
      ),
    );
  }
}
