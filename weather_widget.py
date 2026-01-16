import requests
from flask import Flask, jsonify, render_template_string
import threading
import time

OPENWEATHER_API_KEY = " * "
CITIES = [
    "Tallinn,EE", "Haapsalu,EE", "Narva,EE", "Pärnu,EE", "Kohtla-Järve,EE", "Viljandi,EE", "Rakvere,EE", "Maardu,EE", "Sillamäe,EE", "Kuressaare,EE", "Tartu,EE"
]

app = Flask(__name__)

weather_cache = [{} for _ in CITIES]

# Фоновое обновление погоды

def fetch_weather(city, idx):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=en"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            weather_cache[idx] = {
                "city": data["name"],
                "temp": round(data["main"]["temp"]),
                "desc": data["weather"][0]["description"].capitalize(),
                "icon": f"https://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png"
            }
    except Exception as e:
        print(f"Weather error for {city}: {e}")

def weather_updater():
    while True:
        for idx, city in enumerate(CITIES):
            fetch_weather(city, idx)
            time.sleep(1)  # чтобы не спамить API
        time.sleep(120)  # обновлять каждые 2 минуты

threading.Thread(target=weather_updater, daemon=True).start()

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"UTF-8\" />
<style>
  html, body {
    margin: 0; padding: 0;
    background: rgba(0,0,0,0);
    width: 100vw; height: 100vh;
    overflow: hidden;
    font-family: Arial, sans-serif;
  }
  body {
    position: relative;
    width: 100vw;
    height: 100vh;
  }
  .weather-bar {
    position: fixed;
    top: 24px;
    right: 24px;
    display: flex;
    align-items: center;
    background: rgba(0,0,0,0.65);
    border-radius: 14px;
    box-shadow: 0 0 10px #000a;
    padding: 10px 28px 10px 16px;
    min-width: 180px;
    max-width: 340px;
    height: 56px;
    opacity: 0;
    animation: fadeIn 1s forwards;
    z-index: 9999;
    transition: background 0.5s;
  }
  @keyframes fadeIn { to { opacity: 1; } }
  .icon {
    width: 44px;
    height: 44px;
    object-fit: contain;
    margin-right: 14px;
    flex-shrink: 0;
    background: #2226;
    border-radius: 8px;
    box-shadow: 0 0 6px #0006;
    opacity: 0;
    transition: opacity 0.5s;
  }
  .icon.visible {
    opacity: 1;
  }
  .weather-info {
    display: flex;
    flex-direction: row;
    align-items: center;
    min-width: 0;
    flex: 1;
    gap: 14px;
    opacity: 0;
    filter: brightness(0.7);
    transition: opacity 0.5s, filter 0.5s;
  }
  .weather-info.visible {
    opacity: 1;
    filter: brightness(1);
  }
  .city {
    font-size: 20px;
    font-weight: bold;
    color: #fff;
    max-width: 140px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    transition: color 0.5s;
  }
  .temp {
    font-size: 28px;
    font-weight: bold;
    color: #fff;
    margin-left: 8px;
    min-width: 48px;
    text-align: right;
    transition: color 0.5s;
  }
</style>
<title>Weather in Estonia</title>
</head>
<body>
  <div class=\"weather-bar\">
    <img id=\"icon\" class=\"icon\" src=\"\" alt=\"Weather\">
    <div id=\"weatherInfo\" class=\"weather-info\">
      <span id=\"city\" class=\"city\">City</span>
      <span id=\"temp\" class=\"temp\">0°C</span>
    </div>
  </div>
<script>
  const cities = {{ cities|tojson }};
  let weatherData = [];
  let idx = 0;
  let isFirst = true;

  async function fetchWeather() {
    const resp = await fetch("/weather_api");
    if (resp.ok) {
      weatherData = await resp.json();
    }
  }

  function showCity(i) {
    const icon = document.getElementById("icon");
    const info = document.getElementById("weatherInfo");
    if (!isFirst) {
      icon.classList.remove('visible');
      info.classList.remove('visible');
    }
    setTimeout(() => {
      if (!weatherData[i]) return;
      document.getElementById("city").textContent = weatherData[i].city;
      document.getElementById("temp").textContent = weatherData[i].temp + "°C";
      icon.src = weatherData[i].icon;
      icon.classList.add('visible');
      info.classList.add('visible');
      isFirst = false;
    }, isFirst ? 0 : 600);
  }

  async function cycleCities() {
    await fetchWeather();
    showCity(idx);
    idx = (idx + 1) % cities.length;
    setTimeout(cycleCities, 9000);
  }

  cycleCities();
</script>
</body>
</html>
""", cities=CITIES)

@app.route("/weather_api")
def weather_api():
    return jsonify(weather_cache)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)


