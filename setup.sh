#!/bin/bash
# AI Dublyaj — server'ga avtomatik o'rnatish skripti.
# Ishlatish (server terminalida):
#   git clone https://github.com/zettacodetech/kinodublash.git
#   cd kinodublash && bash setup.sh
set -e

echo "============================================"
echo "   AI Dublyaj — server sozlash"
echo "============================================"

# --- 1. Docker ---
if ! command -v docker >/dev/null 2>&1; then
  echo ">> Docker o'rnatilmoqda..."
  curl -fsSL https://get.docker.com | sudo sh
fi

# --- 2. GPU (agar mavjud bo'lsa) nvidia-container-toolkit ---
GPU=0
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU=1
  if ! sudo docker info 2>/dev/null | grep -qi nvidia; then
    echo ">> nvidia-container-toolkit o'rnatilmoqda (GPU)..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
    sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
  fi
  echo ">> GPU aniqlandi ✅ (voice clone tez ishlaydi)"
else
  echo ">> GPU yo'q — CPU rejimi (dublyaj baribir tez, voice clone sekin)"
fi

# --- 3. .env fayllar + kalitlarni so'rash (nano kerak emas) ---
[ -f 1-backend/.env ] || cp 1-backend/.env.example 1-backend/.env
[ -f 2-telegram-bot/.env ] || cp 2-telegram-bot/.env.example 2-telegram-bot/.env

set_env() {  # fayl kalit qiymat
  if grep -q "^$2=" "$1"; then
    sed -i "s|^$2=.*|$2=\"$3\"|" "$1"
  else
    echo "$2=\"$3\"" >> "$1"
  fi
}

echo ""
echo "============================================"
echo "  Kalitlarni kiriting (joylashtiring + Enter)"
echo "============================================"
read -p "Groq kalit(lar)i (vergul bilan ajrating): " GROQ_KEYS
read -p "Telegram bot token: " BOT_TOKEN

IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")
set_env 1-backend/.env GROQ_API_KEYS "$GROQ_KEYS"
set_env 1-backend/.env BASE_URL "http://$IP:8000"
set_env 2-telegram-bot/.env BOT_TOKEN "$BOT_TOKEN"
[ "$GPU" = "1" ] && set_env 1-backend/.env TTS_PROVIDER "coqui" || set_env 1-backend/.env TTS_PROVIDER "edge"
echo ">> Kalitlar saqlandi ✅"

# --- 4. Ishga tushirish ---
if [ "$GPU" = "1" ]; then
  echo ">> GPU rejimida ishga tushirilyapti..."
  sudo docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
else
  echo ">> CPU rejimida ishga tushirilyapti..."
  sudo docker compose up -d --build
fi

echo ""
echo "============================================"
echo "  ✅ TAYYOR!"
echo "============================================"
sleep 5
sudo docker compose ps
echo ""
echo "Tekshirish:  curl http://localhost:8000/health"
IP=$(curl -s ifconfig.me 2>/dev/null || echo "SERVER_IP")
echo "Web:  http://$IP:3000"
echo "API:  http://$IP:8000/docs"
echo "Bot:  avtomatik ishga tushdi"
