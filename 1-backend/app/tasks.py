"""
Orqa fon (background) dublyaj pipeline'i. FastAPI BackgroundTasks orqali chaqiriladi.
Pipeline: audio ajratish -> transkripsiya -> tarjima -> TTS -> time-stretch -> mux.
Har bosqichda bazadagi progress/stage yangilanadi.
"""
import asyncio
import logging
import shutil

from .config import settings
from .database import AsyncSessionLocal
from .models import TaskStatus, VoiceType
from .services import engine, ffmpeg_core, gender_detect, youtube
from .services.speech_types import SpeechSegment
from . import crud

logger = logging.getLogger("dubbing.pipeline")


async def _set(task_id: str, **fields) -> None:
    async with AsyncSessionLocal() as db:
        await crud.update_task(db, task_id, **fields)


def _clean_segments(segments: list[SpeechSegment], duration: float) -> list[SpeechSegment]:
    """STT segmentlarini chunk chegarasiga moslab, juda qisqa segmentlarni xavfsizlaydi."""
    cleaned: list[SpeechSegment] = []
    for seg in sorted(segments, key=lambda item: item.start):
        text = seg.text.strip()
        if not text:
            continue
        start = max(0.0, min(seg.start, duration))
        end = max(start, min(seg.end, duration))
        if end - start < settings.MIN_SPEECH_SEGMENT_SECONDS:
            end = min(duration, start + settings.MIN_SPEECH_SEGMENT_SECONDS)
        if end <= start:
            continue
        cleaned.append(SpeechSegment(start=start, end=end, text=text))
    return cleaned


async def _cut_reference_audio(
    chunk: str,
    seg: SpeechSegment,
    chunk_dur: float,
    out_path,
):
    wanted = min(
        settings.SPEAKER_REFERENCE_SECONDS,
        max(1.0, seg.duration + (settings.SPEAKER_REFERENCE_PAD_SECONDS * 2)),
    )
    start = max(0.0, min(seg.start - settings.SPEAKER_REFERENCE_PAD_SECONDS, chunk_dur - wanted))
    duration = min(wanted, chunk_dur - start)
    return await ffmpeg_core.extract_audio_clip(chunk, start, duration, out_path)


async def _voice_for_segment(requested_voice: VoiceType, reference_audio) -> VoiceType:
    if requested_voice != VoiceType.AUTO:
        return requested_voice
    detected_voice, _median_f0 = await gender_detect.detect_voice(reference_audio)
    return detected_voice


def _progress_for_segment(chunk_index: int, chunk_count: int, segment_index: int, segment_count: int) -> int:
    total_units = max(1, chunk_count * max(1, segment_count))
    done_units = (chunk_index * max(1, segment_count)) + segment_index
    return 20 + int(68 * done_units / total_units)


async def process_dubbing(task_id: str, source_path: str, voice: VoiceType) -> None:
    """
    Bo'lakli (chunked) dublyaj — 5 soatgacha videolar uchun.
    Audio SEGMENT_SECONDS bo'laklarga bo'linadi; har bo'lak ichidagi nutq
    timestampli segmentlarga ajratilib STT -> tarjima -> speaker-aware TTS qilinadi.
    Har TTS segment original gap davomiyligiga moslanadi, pauzalar silence bilan saqlanadi.
    Bu Groq 25MB audio limitini hal qiladi va sinxronizatsiyani yaxshilaydi.
    """
    temp = settings.temp_dir
    work = temp / task_id
    chunks_dir = work / "chunks"
    seg_dir = work / "segs"
    raw_audio = temp / f"{task_id}_src.wav"
    full_uz = temp / f"{task_id}_uz.wav"
    full_uz_fit = temp / f"{task_id}_uzfit.wav"
    output_path = settings.output_dir / f"{task_id}.mp4"

    try:
        seg_dir.mkdir(parents=True, exist_ok=True)

        await _set(task_id, status=TaskStatus.PROCESSING, stage="audio_extract", progress=8)
        await ffmpeg_core.extract_audio(source_path, raw_audio)

        # AUTO rejimida endi bitta umumiy ovoz tanlanmaydi:
        # har bir gap segmenti uchun reference audio kesilib, alohida voice tanlanadi/klonlanadi.
        if voice == VoiceType.AUTO:
            await _set(task_id, stage="voice_detect", progress=14)

        await _set(task_id, stage="split", progress=18)
        chunks = await ffmpeg_core.split_audio(raw_audio, settings.SEGMENT_SECONDS, chunks_dir)
        if not chunks:
            raise ValueError("Audio bo'laklarga bo'linmadi.")
        n = len(chunks)
        logger.info("Task %s: %d ta bo'lak", task_id, n)

        seg_files: list = []
        orig_parts: list[str] = []
        uz_parts: list[str] = []

        for i, chunk in enumerate(chunks):
            base = 20 + int(68 * i / n)   # progress 20% -> 88%
            chunk_dur = await ffmpeg_core.get_duration(chunk)
            seg_out = seg_dir / f"seg_{i:04d}.wav"

            await _set(task_id, stage="transcribe", progress=base)
            speech_segments = _clean_segments(await engine.transcribe_segments(chunk), chunk_dur)
            if not speech_segments:  # nutqsiz bo'lak -> jimlik (timeline saqlanadi)
                await ffmpeg_core.make_silence(chunk_dur, seg_out)
                seg_files.append(seg_out)
                continue

            # --- Segmentlarni PARALLEL qayta ishlaymiz (tezlashtirish) ---
            await _set(task_id, stage="tts", progress=base)
            sem = asyncio.Semaphore(max(1, settings.SEGMENT_CONCURRENCY))

            async def _render_segment(j, speech, chunk=chunk, chunk_dur=chunk_dur, i=i):
                start = speech.start
                end = max(start, speech.end)
                if end <= start:
                    return None
                segment_dur = end - start
                segment_text = speech.text.strip()
                async with sem:
                    try:
                        uz = await engine.translate_to_uzbek(segment_text)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Task %s: %d/%d tarjima xato (%s).", task_id, i, j, exc)
                        uz = segment_text
                    if not uz.strip():
                        out = seg_dir / f"empty_{i:04d}_{j:03d}.wav"
                        await ffmpeg_core.make_silence(segment_dur, out)
                        return {"j": j, "start": start, "path": out, "orig": segment_text, "uz": ""}
                    ref_audio = seg_dir / f"ref_{i:04d}_{j:03d}.wav"
                    await _cut_reference_audio(str(chunk), SpeechSegment(start=start, end=end, text=segment_text), chunk_dur, ref_audio)
                    segment_voice = await _voice_for_segment(voice, ref_audio)
                    tts_tmp = seg_dir / f"tts_{i:04d}_{j:03d}.wav"
                    fitted = seg_dir / f"part_{i:04d}_{j:03d}.wav"
                    await engine.synthesize_with_reference(uz, segment_voice, tts_tmp, ref_audio)
                    await ffmpeg_core.fit_audio_to_duration(tts_tmp, segment_dur, fitted, max_speedup=settings.MAX_TTS_SPEEDUP, min_slowdown=settings.MIN_TTS_SLOWDOWN)
                    tts_tmp.unlink(missing_ok=True)
                    ref_audio.unlink(missing_ok=True)
                    return {"j": j, "start": start, "path": fitted, "orig": segment_text, "uz": uz}

            rendered = await asyncio.gather(*[_render_segment(j, s) for j, s in enumerate(speech_segments)])

            chunk_parts = []
            real_pos = 0.0
            for r in rendered:
                if not r:
                    continue
                if r["orig"]:
                    orig_parts.append(r["orig"])
                if r["uz"]:
                    uz_parts.append(r["uz"])
                gap_needed = r["start"] - real_pos
                if gap_needed > 0.05:
                    gap = seg_dir / f"gap_{i:04d}_{r['j']:03d}.wav"
                    await ffmpeg_core.make_silence(gap_needed, gap)
                    chunk_parts.append(gap)
                    real_pos += gap_needed
                chunk_parts.append(r["path"])
                real_pos += await ffmpeg_core.get_duration(r["path"])

            # Bo'lakni ANIQ chunk_dur ga tenglaymiz -> bo'lak chegarasi video bilan sinxron qoladi
            if chunk_parts:
                raw_seg = seg_dir / f"raw_{i:04d}.wav"
                await ffmpeg_core.concat_audio(chunk_parts, raw_seg)
                await ffmpeg_core.set_exact_duration(raw_seg, chunk_dur, seg_out)
                raw_seg.unlink(missing_ok=True)
            else:
                await ffmpeg_core.make_silence(chunk_dur, seg_out)
            seg_files.append(seg_out)

        await _set(
            task_id, stage="concat", progress=90,
            original_text=" ".join(orig_parts)[:8000],
            translated_text=" ".join(uz_parts)[:8000],
        )
        await ffmpeg_core.concat_audio(seg_files, full_uz)

        # Audioni ANIQ video davomiyligiga tenglaymiz — natija video bilan to'liq
        # mos bo'lsin (oxiri kesilmasin, sinxron saqlansin).
        video_duration = await ffmpeg_core.get_duration(source_path)
        await ffmpeg_core.set_exact_duration(full_uz, video_duration, full_uz_fit)

        await _set(task_id, stage="mux", progress=96)
        await ffmpeg_core.mux_audio_into_video(source_path, full_uz_fit, output_path)

        await _set(
            task_id, status=TaskStatus.COMPLETED, stage="completed", progress=100,
            output_path=str(output_path),
        )
        logger.info("Task %s muvaffaqiyatli yakunlandi (%d bo'lak).", task_id, n)

    except Exception as exc:  # noqa: BLE001 — barcha xatolarni bazaga yozamiz
        logger.exception("Task %s xatolik bilan tugadi", task_id)
        error_text = str(exc).strip() or f"{type(exc).__name__}: {exc!r}"
        await _set(task_id, status=TaskStatus.FAILED, stage="failed", error=error_text[:2000])
    finally:
        raw_audio.unlink(missing_ok=True)
        full_uz.unlink(missing_ok=True)
        full_uz_fit.unlink(missing_ok=True)
        shutil.rmtree(work, ignore_errors=True)


async def process_dubbing_from_url(task_id: str, url: str, source_path: str, voice: VoiceType) -> None:
    """Avval havoladan videoni yuklab oladi, so'ng odatiy dublyaj pipeline'ini ishga tushiradi."""
    try:
        await _set(task_id, status=TaskStatus.PROCESSING, stage="download", progress=5)
        real_path = await youtube.download(url, source_path)
        await _set(task_id, source_path=str(real_path))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Task %s: havoladan yuklab olishda xatolik", task_id)
        await _set(task_id, status=TaskStatus.FAILED, stage="failed", error=str(exc)[:2000])
        return

    await process_dubbing(task_id, str(real_path), voice)
