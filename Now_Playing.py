import requests
from flask import Flask, jsonify, render_template_string, request

AZURACAST_API_URL = " * "
AUDIO_STREAM_URL = " * "

app = Flask(__name__)

nowplaying_cache = {
    "title": "Загрузка...",
    "artist": "Неизвестный исполнитель",
    "cover": "https://via.placeholder.com/1000x1000.png?text=No+Cover",
    "stream": AUDIO_STREAM_URL,
}


def fetch_nowplaying():
    try:
        response = requests.get(AZURACAST_API_URL, timeout=6)
        if response.status_code == 200:
            data = response.json()
            song = data.get("now_playing", {}).get("song", {})
            nowplaying_cache["title"] = song.get("title", nowplaying_cache["title"] or "Без названия")
            nowplaying_cache["artist"] = song.get("artist", nowplaying_cache["artist"] or "Неизвестный исполнитель")
            nowplaying_cache["cover"] = song.get("art") or nowplaying_cache["cover"]

            possible_stream = (
                data.get("now_playing", {}).get("song", {}).get("url")
                or data.get("listen_url")
                or data.get("station", {}).get("listen_url")
                or data.get("station", {}).get("stream_url")
                or data.get("station", {}).get("listen_url_local")
            )
            if possible_stream:
                nowplaying_cache["stream"] = possible_stream
            else:
                nowplaying_cache["stream"] = nowplaying_cache.get("stream", AUDIO_STREAM_URL)
    except Exception as e:
        print("Ошибка при получении данных из AzuraCast:", e)


@app.route("/")
def index():
    # debug включается через параметр ?debug=1
    debug = request.args.get("debug", "0") == "1"
    return render_template_string(
        """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8" />
<title>Haapsaly Bassline — Now Playing</title>
<style>
  html, body {
    margin: 0; padding: 0;
    width: 100%; height: 100%;
    overflow: hidden;
    background: black;
    font-family: "Segoe UI", Arial, sans-serif;
  }

  .bg {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    object-fit: cover;
    filter: blur(25px) brightness(0.4);
    transform: scale(1.1);
    transition: opacity 0.6s ease;
    z-index: 0;
  }

  .info-box {
    position: fixed;
    bottom: 40px;
    left: 40px;
    display: flex;
    align-items: center;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 12px 20px 12px 12px;
    color: white;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6);
    opacity: 0;
    animation: fadeIn 1s forwards;
    z-index: 2;
  }

  @keyframes fadeIn {
    to { opacity: 1; }
  }

  .cover-small {
    width: 70px;
    height: 70px;
    object-fit: cover;
    border-radius: 12px;
    margin-right: 16px;
    flex-shrink: 0;
  }

  .text-block {
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
  }

  .title {
    font-size: 1.1em;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 340px;
  }

  .artist {
    font-size: 0.9em;
    color: #ccc;
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 340px;
  }

  @keyframes scrollText {
    0% { transform: translateX(0); }
    10% { transform: translateX(0); }
    90% { transform: translateX(calc(-100% + 340px)); }
    100% { transform: translateX(calc(-100% + 340px)); }
  }

  .scroll {
    display: inline-block;
    animation: scrollText 10s linear infinite;
  }

  audio {
    display: none;
  }

  /* Небольшой видимый лог (включается только при debug=true) */
  #statusLog {
    position: fixed;
    top: 8px;
    right: 8px;
    max-width: 420px;
    max-height: 40vh;
    overflow: auto;
    background: rgba(0,0,0,0.55);
    color: #0f0;
    font-family: monospace;
    font-size: 12px;
    padding: 8px;
    border-radius: 8px;
    z-index: 9999;
    box-shadow: 0 4px 18px rgba(0,0,0,0.7);
  }
</style>
</head>
<body>
  <img id="bg" class="bg" src="https://via.placeholder.com/1920x1080?text=No+Cover" alt="Background">

  <div class="info-box">
    <img id="coverSmall" class="cover-small" src="https://via.placeholder.com/1000x1000.png?text=No+Cover" alt="Cover">
    <div class="text-block">
      <div id="title" class="title">Загрузка...</div>
      <div id="artist" class="artist">Неизвестный исполнитель</div>
    </div>
  </div>

  <!-- Аудиоплеер -->
  <audio id="audioPlayer" autoplay playsinline>
    <source src="{{ stream }}" type="audio/mpeg">
  </audio>

  {%- if debug %}
  <!-- Видимый лог (отображается только если ?debug=1) -->
  <div id="statusLog" aria-hidden="false"></div>
  {%- endif %}

<script>
const audio = document.getElementById("audioPlayer");
const sourceEl = audio.querySelector('source');
let BASE_STREAM = "{{ stream }}";

// DEBUG флаг: будет true/false в JS
const DEBUG = {{ 'true' if debug else 'false' }};

// Логирование — всегда в консоль, в DOM только при DEBUG
function log(message, level = 'info') {
  try {
    const ts = new Date().toISOString().replace('T', ' ').replace('Z','');
    const line = `[${ts}] ${message}`;
    console[level === 'error' ? 'error' : 'log'](line);
    if (DEBUG) {
      const logEl = document.getElementById('statusLog');
      if (logEl) {
        const p = document.createElement('div');
        p.textContent = line;
        p.style.color = level === 'error' ? '#ff8080' : '#b7ffb7';
        logEl.appendChild(p);
        while (logEl.childElementCount > 200) logEl.removeChild(logEl.firstChild);
        logEl.scrollTop = logEl.scrollHeight;
      }
    }
  } catch (e) {
    console.warn('log error', e);
  }
}

// Остальная логика остаётся без изменений (reconnect, health checks, nowplaying update)
// Попытка автозапуска
window.addEventListener("load", () => {
  audio.play().then(() => {
    log('Auto-play started');
  }).catch(err => {
    log('Автозапуск заблокирован браузером: ' + err, 'error');
    if (DEBUG) {
      const btn = document.createElement("button");
      btn.textContent = "▶ Включить звук";
      Object.assign(btn.style, {
        position: "fixed",
        top: "50%", left: "50%",
        transform: "translate(-50%, -50%)",
        padding: "12px 24px",
        fontSize: "18px",
        borderRadius: "12px",
        border: "none",
        background: "#00ff88",
        color: "#000",
        cursor: "pointer",
        boxShadow: "0 0 20px rgba(0,255,136,0.6)",
        zIndex: 9999
      });
      btn.onclick = () => {
        audio.play();
        btn.remove();
      };
      document.body.appendChild(btn);
    }
  });
});

// --- reconnect logic for long-lived streams ---
let reconnectAttempts = 0;
let reconnectTimer = null;
const MAX_BACKOFF_MS = 30000;
const MAX_ATTEMPTS_BEFORE_FULL_RELOAD = 8;

function setAudioSource(newUrl, useCacheBuster = true) {
  try {
    if (!newUrl) return;
    let finalUrl = newUrl;
    if (useCacheBuster) {
      finalUrl = newUrl + (newUrl.includes('?') ? '&' : '?') + '_=' + Date.now();
    }
    if (sourceEl.src === finalUrl) {
      return;
    }
    sourceEl.src = finalUrl;
    audio.load();
    log('Set audio source: ' + finalUrl);
  } catch (e) {
    log('setAudioSource error: ' + e, 'error');
  }
}

function reconnectAudio(forceCacheBuster = true, optionalStream) {
  try {
    if (optionalStream) {
      BASE_STREAM = optionalStream;
      log('Updated BASE_STREAM to: ' + optionalStream);
    }
    setAudioSource(BASE_STREAM, forceCacheBuster);
    audio.play().then(() => {
      log('Audio playback started/restarted');
      reconnectAttempts = 0;
      if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    }).catch(err => {
      log('Play failed during reconnect: ' + err, 'error');
      scheduleReconnect();
    });
  } catch (e) {
    log('reconnectAudio error: ' + e, 'error');
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectAttempts++;
  if (reconnectAttempts >= MAX_ATTEMPTS_BEFORE_FULL_RELOAD) {
    log('Достигнут лимит попыток (' + reconnectAttempts + ') — перезагрузка страницы как крайняя мера', 'error');
    setTimeout(() => {
      try { window.location.reload(true); } catch (e) { window.location.reload(); }
    }, 1500);
    return;
  }
  const delay = Math.min(MAX_BACKOFF_MS, 1000 * Math.pow(2, Math.min(reconnectAttempts - 1, 6)));
  log('Scheduling reconnect in ' + delay + ' ms (attempt ' + reconnectAttempts + ')');
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    reconnectAudio(true);
  }, delay);
}

['error', 'stalled', 'suspend', 'emptied', 'abort', 'ended', 'waiting'].forEach(ev => {
  audio.addEventListener(ev, (e) => {
    log('Audio event: ' + ev + ' — scheduling reconnect', 'error');
    scheduleReconnect();
  });
});

audio.addEventListener('playing', () => {
  reconnectAttempts = 0;
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  log('Audio playing — reset reconnect attempts');
});

setInterval(() => {
  try {
    if (audio.paused || audio.readyState < 3) {
      log('Health check: paused=' + audio.paused + ', readyState=' + audio.readyState, 'error');
      scheduleReconnect();
    }
  } catch (e) {
    log('health check error: ' + e, 'error');
  }
}, 60_000);

// --- now playing update logic (и динамический stream) ---
async function updateNowPlaying() {
  try {
    const resp = await fetch("/nowplaying_api");
    if (!resp.ok) throw new Error("Ошибка сети: " + resp.status);
    const data = await resp.json();

    const titleElem = document.getElementById("title");
    const artistElem = document.getElementById("artist");
    const coverSmall = document.getElementById("coverSmall");
    const bg = document.getElementById("bg");

    if (titleElem.textContent !== data.title) titleElem.textContent = data.title;
    if (artistElem.textContent !== data.artist) artistElem.textContent = data.artist;

    if (coverSmall.src !== data.cover) {
      coverSmall.style.opacity = 0;
      bg.style.opacity = 0;
      coverSmall.onload = () => coverSmall.style.opacity = 1;
      bg.onload = () => bg.style.opacity = 1;
      coverSmall.src = data.cover;
      bg.src = data.cover;
    }

    if (data.stream && data.stream !== BASE_STREAM) {
      log('nowplaying_api предоставил новый stream: ' + data.stream);
      reconnectAudio(true, data.stream);
    }

    [titleElem, artistElem].forEach(el => {
      el.classList.remove("scroll");
      if (el.scrollWidth > el.clientWidth) el.classList.add("scroll");
    });

  } catch (e) {
    log('Ошибка обновления nowplaying: ' + e, 'error');
  }
}

setAudioSource(BASE_STREAM, true);
updateNowPlaying();
setInterval(updateNowPlaying, 3000);
</script>
</body>
</html>
""",
        stream=AUDIO_STREAM_URL,
        debug=debug,
    )


@app.route("/nowplaying_api")
def nowplaying_api():
    fetch_nowplaying()
    return jsonify(nowplaying_cache)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
