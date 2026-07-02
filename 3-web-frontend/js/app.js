/**
 * AI Dublyaj — Frontend mantiqi (Fetch API).
 * Videoni /dub ga yuboradi, /status ni interval orqali tekshiradi,
 * tayyor bo'lganda <video> pleyerda ochadi.
 */
(() => {
  "use strict";

  const CFG = window.APP_CONFIG;
  const API = CFG.BACKEND_URL.replace(/\/$/, "");

  // Telegram Web App integratsiyasi (agar ichida ochilgan bo'lsa)
  const tg = window.Telegram?.WebApp;
  let tgUser = null;
  if (tg) {
    tg.ready();
    tg.expand();
    tgUser = tg.initDataUnsafe?.user || null;
  }

  // DOM
  const el = (id) => document.getElementById(id);
  const dropzone = el("dropzone");
  const fileInput = el("file-input");
  const filePreview = el("file-preview");
  const fileName = el("file-name");
  const fileSize = el("file-size");
  const fileRemove = el("file-remove");
  const startBtn = el("start-btn");
  const urlInput = el("url-input");
  const errorBox = el("error-box");

  const uploadSection = el("upload-section");
  const progressSection = el("progress-section");
  const resultSection = el("result-section");

  const progressRing = el("progress-ring");
  const progressPercent = el("progress-percent");
  const progressStage = el("progress-stage");
  const progressEta = el("progress-eta");

  const resultVideo = el("result-video");
  const downloadBtn = el("download-btn");
  const restartBtn = el("restart-btn");

  const RING_CIRCUMFERENCE = 264; // 2*pi*42
  const STAGE_LABELS = {
    queued: "⏳ Navbatda...",
    download: "⬇️ Havoladan yuklab olinmoqda...",
    audio_extract: "🎧 Audio ajratilmoqda...",
    voice_detect: "🕵️ Ovoz turi aniqlanmoqda...",
    transcribe: "📝 Nutq matnga o'girilmoqda...",
    translate: "🌐 AI tarjima qilmoqda...",
    tts: "🔊 Ovoz generatsiya qilinmoqda...",
    time_stretch: "⏱ Vaqt moslashtirilmoqda...",
    mux: "🎬 Video yig'ilmoqda...",
    completed: "✅ Tayyor!",
  };

  let selectedFile = null;
  let pollTimer = null;

  // ---------- Fayl tanlash ----------
  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => handleFile(e.target.files[0]));

  ["dragenter", "dragover"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    })
  );
  dropzone.addEventListener("drop", (e) => handleFile(e.dataTransfer.files[0]));

  fileRemove.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    filePreview.classList.add("hidden");
    dropzone.classList.remove("hidden");
  });

  function handleFile(file) {
    hideError();
    if (!file) return;
    if (!file.type.startsWith("video/")) {
      return showError("Faqat video fayl tanlang.");
    }
    if (file.size > CFG.MAX_UPLOAD_MB * 1024 * 1024) {
      return showError(`Fayl ${CFG.MAX_UPLOAD_MB}MB dan katta bo'lmasligi kerak.`);
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatSize(file.size);
    filePreview.classList.remove("hidden");
    dropzone.classList.add("hidden");
  }

  // ---------- Dublyajni boshlash ----------
  startBtn.addEventListener("click", async () => {
    hideError();
    const voice = document.querySelector('input[name="voice"]:checked').value;
    const url = urlInput.value.trim();

    if (!selectedFile && !url) return showError("Video tanlang yoki havola joylang.");

    switchTo("progress");
    setProgress(0, url ? "download" : "queued");
    progressEta.textContent = "";

    try {
      const data = url ? await submitDubUrl(url, voice) : await submitDub(selectedFile, voice);
      if (data.eta_text) progressEta.textContent = "⏱ Taxminiy vaqt: " + data.eta_text;
      pollStatus(data.task_id);
    } catch (err) {
      switchTo("upload");
      showError("Yuborishda xatolik: " + err.message);
    }
  });

  async function submitDubUrl(url, voice) {
    const body = { url, voice };
    if (tgUser) {
      body.external_id = String(tgUser.id);
      body.username = tgUser.username || "";
      body.full_name = `${tgUser.first_name || ""} ${tgUser.last_name || ""}`.trim();
    }
    const resp = await fetch(`${API}/dub-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`Server ${resp.status}`);
    return await resp.json();
  }

  async function submitDub(file, voice) {
    const form = new FormData();
    form.append("file", file);
    if (tgUser) {
      form.append("external_id", String(tgUser.id));
      form.append("username", tgUser.username || "");
      form.append("full_name", `${tgUser.first_name || ""} ${tgUser.last_name || ""}`.trim());
    }
    const resp = await fetch(`${API}/dub?voice=${voice}`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`Server ${resp.status}`);
    return await resp.json();
  }

  // ---------- Status polling ----------
  function pollStatus(taskId) {
    clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      try {
        const resp = await fetch(`${API}/status/${taskId}`);
        if (!resp.ok) throw new Error(`Status ${resp.status}`);
        const data = await resp.json();

        setProgress(data.progress || 0, data.stage);
        if (data.eta_text && data.status !== "completed") {
          progressEta.textContent = "⏱ Taxminiy vaqt: " + data.eta_text;
        }

        if (data.status === "completed") {
          clearInterval(pollTimer);
          showResult(data.download_url);
        } else if (data.status === "failed") {
          clearInterval(pollTimer);
          switchTo("upload");
          showError("Render xatoligi: " + (data.error || "nomaʼlum"));
        }
      } catch (err) {
        clearInterval(pollTimer);
        switchTo("upload");
        showError("Aloqa uzildi: " + err.message);
      }
    }, CFG.POLL_INTERVAL);
  }

  // ---------- Natija ----------
  function showResult(downloadUrl) {
    setProgress(100, "completed");
    setTimeout(() => {
      resultVideo.src = downloadUrl;
      downloadBtn.href = downloadUrl;
      switchTo("result");
    }, 600);
  }

  restartBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    urlInput.value = "";
    resultVideo.src = "";
    filePreview.classList.add("hidden");
    dropzone.classList.remove("hidden");
    switchTo("upload");
  });

  // ---------- Yordamchilar ----------
  function setProgress(percent, stage) {
    const p = Math.max(0, Math.min(100, percent));
    progressRing.style.strokeDashoffset = RING_CIRCUMFERENCE * (1 - p / 100);
    progressPercent.textContent = `${p}%`;
    if (stage && STAGE_LABELS[stage]) progressStage.textContent = STAGE_LABELS[stage];
  }

  function switchTo(view) {
    uploadSection.classList.toggle("hidden", view !== "upload");
    progressSection.classList.toggle("hidden", view !== "progress");
    resultSection.classList.toggle("hidden", view !== "result");
  }

  function showError(msg) {
    errorBox.textContent = "⚠️ " + msg;
    errorBox.classList.remove("hidden");
  }
  function hideError() {
    errorBox.classList.add("hidden");
  }

  function formatSize(bytes) {
    const mb = bytes / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
  }
})();
