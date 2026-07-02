FROM python:3.12-slim

# FFmpeg — dublyaj yadrosi uchun majburiy
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 180 --retries 15 -r requirements.txt

# yt-dlp NIGHTLY — YouTube o'zgarishlariga eng tez moslashadi
RUN pip install --no-cache-dir --pre -U "yt-dlp[default]"

# Voice cloning (Coqui XTTS v2) — CPU torch + coqui-tts.
# ISHLAYDIGAN kombinatsiya (pin): torch 2.4.1 + transformers 4.46.2 + coqui-tts 0.25.1
# (yangi versiyalar torchcodec/isin_mps_friendly xatolarini beradi).
RUN pip install --no-cache-dir --timeout 300 --retries 30 torch==2.4.1 torchaudio==2.4.1 \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --timeout 300 --retries 30 "coqui-tts==0.25.1" "transformers==4.46.2"

COPY . .

RUN mkdir -p storage/uploads storage/outputs storage/temp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
