import requests
from flask import Flask, jsonify, render_template_string

AZURACAST_API_URL = "http://hpsbassline.myftp.biz:90/api/station/haapsaly_bassline/nowplaying"
AUDIO_STREAM_URL = "http://hpsbassline.myftp.biz:90/listen/haapsaly_bassline/radio.flac"

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
            nowplaying_cache['title'] = song.get("title", "Без названия")
            nowplaying_cache['artist'] = song.get("artist", "Неизвестный исполнитель")
            nowplaying_cache['cover'] = song.get("art") or nowplaying_cache['cover']
    except Exception as e:
        print("Ошибка при получении данных:", e)

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8" />
<style>
  html, body {
    margin: 0; padding: 0;
    background: rgba(0,0,0,0);
    width: 100%; height: 100%;
    overflow: hidden;
    font-family: Arial, sans-serif;
  }
  .container {
    position: absolute;
    bottom: 20px;
    left: 20px;
    border-radius: 16px;
    padding: 12px;
    display: flex;
    align-items: center;
    color: white;
    box-shadow: 0 0 12px #000;
    min-width: 300px;
    background-color: rgba(0,0,0,0.3);
    transition: background-color 0.5s ease;
  }
  .cover {
    width: 80px;
    height: 80px;
    object-fit: cover;
    border-radius: 8px;
    margin-right: 12px;
  }
  .text {
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .title {
    margin: 0; padding: 0;
    font-size: 18px;
    font-weight: bold;
    color: #fff;
  }
  .artist {
    margin: 4px 0 0 0;
    padding: 0;
    font-size: 14px;
    color: #ccc;
  }
  audio {
    width: 0;
    height: 0;
    opacity: 0;
    position: fixed;
  }
</style>
<title>Now Playing</title>
</head>
<body>
  <div class="container" id="container">
    <img id="cover" class="cover" src="https://via.placeholder.com/1000x1000.png?text=No+Cover" alt="Обложка">
    <div class="text">
      <div id="title" class="title">Загрузка...</div>
      <div id="artist" class="artist">Неизвестный исполнитель</div>
    </div>
  </div>

  <audio id="audioPlayer" autoplay playsinline>
    <source src="{{ stream }}" type="audio/flac">
    Ваш браузер не поддерживает воспроизведение аудио.
  </audio>

<script>
  async function getAverageColor(imgElem) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = "Anonymous";
      img.src = imgElem.src;

      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0);

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        let r = 0, g = 0, b = 0;
        let count = 0;

        for(let i = 0; i < imageData.data.length; i += 4) {
          const alpha = imageData.data[i+3];
          if (alpha > 125) {
            r += imageData.data[i];
            g += imageData.data[i+1];
            b += imageData.data[i+2];
            count++;
          }
        }
        if (count === 0) return resolve("rgba(0,0,0,0.3)");
        r = Math.round(r / count);
        g = Math.round(g / count);
        b = Math.round(b / count);
        resolve(`rgba(${r},${g},${b},0.3)`);
      };

      img.onerror = () => reject("Не удалось загрузить изображение");
    });
  }

  async function updateNowPlaying() {
    try {
      const resp = await fetch("/nowplaying_api");
      if (!resp.ok) throw new Error("Ошибка сети");
      const data = await resp.json();

      const titleElem = document.getElementById("title");
      const artistElem = document.getElementById("artist");
      const coverElem = document.getElementById("cover");
      const container = document.getElementById("container");

      if (titleElem.textContent !== data.title) {
        titleElem.textContent = data.title;
      }
      if (artistElem.textContent !== data.artist) {
        artistElem.textContent = data.artist;
      }
      if (coverElem.src !== data.cover) {
        coverElem.src = data.cover;

        coverElem.onload = async () => {
          try {
            const avgColor = await getAverageColor(coverElem);
            container.style.backgroundColor = avgColor;
          } catch(e) {
            container.style.backgroundColor = "rgba(0,0,0,0.3)";
          }
        };
      }
    } catch(e) {
      console.error("Ошибка обновления:", e);
    }
  }

  updateNowPlaying();
  setInterval(updateNowPlaying, 3000);
</script>
</body>
</html>
""", stream=AUDIO_STREAM_URL)

@app.route("/nowplaying_api")
def nowplaying_api():
    fetch_nowplaying()
    return jsonify({
        "title": nowplaying_cache["title"],
        "artist": nowplaying_cache["artist"],
        "cover": nowplaying_cache["cover"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
