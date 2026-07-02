# Google Cloud'ga deploy (GPU VM + Docker)

Bu qo'llanma tizimni **Compute Engine GPU VM** ga o'rnatadi (voice clone tez ishlaydi).

## 0. Talablar
- Google Cloud akkaunt + billing yoqilgan ($300 bepul kredit)
- **GPU kvota:** yangi akkauntda GPU kvotasi 0 bo'ladi. Console → IAM & Admin → Quotas →
  "NVIDIA T4 GPUs" ni qidirib, 1 ga oshirishni so'rang (odatda bir necha daqiqa/soatda tasdiqlanadi).

## 1. VM yaratish
Console → Compute Engine → Create Instance, yoki gcloud:
```bash
gcloud compute instances create kinodublash \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --image-family=ubuntu-2204-lts --image-project=ubuntu-os-cloud \
  --boot-disk-size=120GB \
  --tags=http-server,https-server
```

## 2. Firewall (portlar)
```bash
gcloud compute firewall-rules create allow-dub \
  --allow=tcp:8000,tcp:3000 --target-tags=http-server
```

## 3. VM ga SSH + o'rnatish
```bash
gcloud compute ssh kinodublash --zone=us-central1-a
```
VM ichida:
```bash
# NVIDIA drayver
sudo apt-get update && sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall && sudo reboot   # reboot'dan keyin qayta SSH

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker

# nvidia-container-toolkit (Docker'da GPU)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
nvidia-smi   # GPU ko'rinishi kerak
```

## 4. Loyihani klonlash
```bash
git clone https://github.com/zettacodetech/kinodublash.git
cd kinodublash
```
> Private repo bo'lsa: `git clone https://<TOKEN>@github.com/zettacodetech/kinodublash.git`

## 5. Maxfiy sozlamalar (repo'da yo'q — qo'lda yaratiladi)
```bash
cp 1-backend/.env.example 1-backend/.env
nano 1-backend/.env      # GROQ_API_KEYS, BASE_URL ni to'ldiring; TTS_PROVIDER=coqui (GPU'da tez)

cp 2-telegram-bot/.env.example 2-telegram-bot/.env
nano 2-telegram-bot/.env # BOT_TOKEN ni yozing

# YouTube uchun cookies (ixtiyoriy):
# cookies.txt ni 1-backend/storage/cookies.txt ga joylang
```

## 6. XTTS modelini oldindan yuklash (voice clone uchun)
```bash
mkdir -p tts-model
cd tts-model
for f in config.json vocab.json speakers_xtts.pth model.pth; do
  curl -L -C - -o $f "https://huggingface.co/coqui/XTTS-v2/resolve/main/$f"
done
echo agreed > tos_agreed.txt
cd ..
# volume'ga joylash uchun keyin bir marta: docker cp tts-model/. <api_container>:/root/.local/share/tts/tts_models--multilingual--multi-dataset--xtts_v2/
```

## 7. Ishga tushirish (GPU bilan)
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
docker compose ps
curl http://localhost:8000/health
```

## 8. Kirish
- API:  `http://<VM_TASHQI_IP>:8000/docs`
- Web:  `http://<VM_TASHQI_IP>:3000`
- Bot:  avtomatik ishga tushadi (@kinodublashbot)

## Eslatma
- **Domen + HTTPS** uchun `1-backend/nginx.conf.example` dan foydalaning (Caddy/Nginx + Let's Encrypt).
- GPU'da `TTS_PROVIDER=coqui` — voice clone tez. CPU'ga qaytish: `TTS_PROVIDER=edge`.
- VM to'xtatilsa GPU haqi to'xtaydi (kreditni tejash uchun ishlatmaganda `gcloud compute instances stop`).
