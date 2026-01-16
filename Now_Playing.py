import requests
from flask import Flask, jsonify, render_template_string

AZURACAST_API_URL = "https://azura.hpsbassline.myftp.biz/api/station/haapsaly_bassline/nowplaying"
AUDIO_STREAM_URL = "https://azura.hpsbassline.myftp.biz/listen/haapsaly_bassline/radio.mp3"

app = Flask(__name__)

nowplaying_cache = {
    "title": "Загрузка...",
    "artist": "Неизвестный исполнитель",
    "cover": "https://via.placeholder.com/1000x1000.png?text=No+Cover",
}


def fetch_nowplaying():
    try:
        response = requests.get(AZURACAST_API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            song = data.get("now_playing", {}).get("song", {})
            nowplaying_cache["title"] = song.get("title", "Без названия")
            nowplaying_cache["artist"] = song.get("artist", "Неизвестный исполнитель")
            nowplaying_cache["cover"] = song.get("art") or nowplaying_cache["cover"]
    except Exception as e:
        print("Ошибка при получении данных:", e)


@app.route("/")
def index():
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

<script>
const audio = document.getElementById("audioPlayer");

// Попытка автозапуска
window.addEventListener("load", () => {
  audio.play().then(() => {
    console.log("Автозапуск успешен");
  }).catch(err => {
    console.warn("Автозапуск заблокирован браузером:", err);
    // В случае блокировки — показываем кнопку "Нажми, чтобы включить"
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
  });
});

async function updateNowPlaying() {
  try {
    const resp = await fetch("/nowplaying_api");
    if (!resp.ok) throw new Error("Ошибка сети");
    const data = await resp.json();

    const titleElem = document.getElementById("title");
    const artistElem = document.getElementById("artist");
    const coverSmall = document.getElementById("coverSmall");
    const bg = document.getElementById("bg");

    // Обновляем текст
    if (titleElem.textContent !== data.title)
      titleElem.textContent = data.title;

    if (artistElem.textContent !== data.artist)
      artistElem.textContent = data.artist;

    // Плавная смена обложки
    if (coverSmall.src !== data.cover) {
      coverSmall.style.opacity = 0;
      bg.style.opacity = 0;

      coverSmall.onload = () => coverSmall.style.opacity = 1;
      bg.onload = () => bg.style.opacity = 1;

      coverSmall.src = data.cover;
      bg.src = data.cover;
    }

    // Добавляем автоскролл
    [titleElem, artistElem].forEach(el => {
      el.classList.remove("scroll");
      if (el.scrollWidth > el.clientWidth) el.classList.add("scroll");
    });

  } catch (e) {
    console.error("Ошибка обновления:", e);
  }
}

updateNowPlaying();
setInterval(updateNowPlaying, 3000);
</script>
</body>
</html>
""",
        stream=AUDIO_STREAM_URL,
    )


@app.route("/nowplaying_api")
def nowplaying_api():
    fetch_nowplaying()
    return jsonify(nowplaying_cache)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
