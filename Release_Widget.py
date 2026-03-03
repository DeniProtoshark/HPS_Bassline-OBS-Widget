import requests
from flask import Flask, jsonify, render_template_string
from dateutil import parser as date_parser
from datetime import datetime, timezone
import threading
import time

# ===================== КОНФИГУРАЦИЯ =====================
# Источник данных
RELEASE_URL = "https://release.hpsbassline.club/api/releases"

# Логика отбора релизов
DISPLAY_DAYS = 0                     # сколько дней считаем "новым" (0 = только сегодня)
MAX_OLD_RELEASES = 10                 # сколько старых показывать, если нет новых

# Обновление кэша
CACHE_REFRESH_MINUTES = 10            # как часто обновлять список релизов

# ========== НАСТРОЙКИ ТАЙМИНГОВ (в миллисекундах) ==========
SWITCH_INTERVAL = 20000                # интервал смены релиза (мс)
FLIP_DELAY = 2000                       # через сколько мс после показа перевернуть на QR
FLIP_DURATION = 800                     # длительность анимации переворота (мс)
FADE_DURATION = 600                      # длительность fade-in/fade-out при смене (мс)
FADE_DELAY_BEFORE_UPDATE = 200           # задержка перед обновлением HTML после fade-out (чтобы анимация успела завершиться)

# Опции поворота обратно (если нужно, чтобы карточка возвращалась на лицевую сторону)
ENABLE_BACK_FLIP = True                 # включить ли автоматический поворот обратно?
BACK_FLIP_DELAY = 10000                    # через сколько мс после переворота вернуться обратно (если ENABLE_BACK_FLIP = True)

# ========== НАСТРОЙКИ QR-КОДА ==========
QR_SIZE = 320                            # размер QR, запрашиваемый у API (пиксели)
QR_MAX_WIDTH = "98%"                      # максимальная ширина внутри контейнера (проценты)
QR_MAX_HEIGHT = "98%"                     # максимальная высота
QR_OBJECT_FIT = "contain"                  # contain (вписать) / cover (заполнить)

# ========== НАСТРОЙКИ ВНЕШНЕГО ВИДА ==========
# Основной виджет
WIDGET_WIDTH = "min(340px, 92vw)"        # ширина
WIDGET_BG = "rgba(0, 0, 0, 0.45)"        # фон
WIDGET_BLUR = "6px"                       # размытие фона
WIDGET_PADDING = "18px"                   # внутренние отступы
WIDGET_BORDER_RADIUS = "14px"             # скругление углов
WIDGET_BOX_SHADOW = "0 0 25px rgba(0,0,0,0.4)"  # тень

# Блок с обложкой (флип)
FLIPPER_ASPECT_RATIO = "1 / 1"            # соотношение сторон (квадрат)
FRONT_BG_SIZE = "cover"                    # как заполнять обложку (cover/contain)
FRONT_BG_POSITION = "center"               # позиция обложки

# Задняя сторона (QR)
BACK_BG = "rgba(0, 0, 0, 0.7)"             # фон задней стороны

# Текстовая информация
INFO_GAP = "4px"                           # отступы между строками
TITLE_FONT_SIZE = "clamp(18px, 3vw, 24px)"
TITLE_FONT_WEIGHT = "700"
AUTHOR_FONT_SIZE = "clamp(14px, 2.5vw, 18px)"
AUTHOR_OPACITY = "0.9"
ALBUM_FONT_SIZE = "clamp(12px, 2vw, 16px)"
ALBUM_OPACITY = "0.6"
ALBUM_TEXT_TRANSFORM = "uppercase"
ALBUM_LETTER_SPACING = "1px"

# Бейдж NEW
SHOW_BADGE = True                           # показывать ли бейдж
BADGE_TEXT = "NEW"                          # текст бейджа
BADGE_BG = "#7a3cff"                         # цвет фона
BADGE_COLOR = "white"                        # цвет текста
BADGE_PADDING = "4px 8px"
BADGE_BORDER_RADIUS = "10px"
BADGE_FONT_SIZE = "clamp(10px, 2vw, 12px)"
BADGE_FONT_WEIGHT = "600"
# ========================================================

app = Flask(__name__)
cached_releases = []

def fetch_releases():
    try:
        r = requests.get(RELEASE_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        releases = []
        for item in data:
            cover = item.get("cover", "")
            if cover.startswith("/"):
                cover = "https://release.hpsbassline.club" + cover
            slug = item.get("slug", "")
            releases.append({
                "title": item.get("title", ""),
                "author": item.get("artist", ""),
                "album": slug,
                "slug": slug,
                "cover": cover,
                "date": item.get("createdAt", "")
            })
        return releases
    except Exception as e:
        print("Fetch error:", e)
        return []

def process_releases(releases):
    now = datetime.now(timezone.utc)
    new = []
    old = []
    for r in releases:
        try:
            release_date = date_parser.parse(r["date"])
            if release_date.tzinfo is None:
                release_date = release_date.replace(tzinfo=timezone.utc)
            days_old = (now - release_date).days
            if 0 <= days_old <= DISPLAY_DAYS:
                r["is_new"] = True
                new.append(r)
            else:
                r["is_new"] = False
                old.append(r)
        except Exception as e:
            print("Date parse error:", e, r)
            continue
    new.sort(key=lambda x: x["date"], reverse=True)
    old.sort(key=lambda x: x["date"], reverse=True)
    return new if new else old[:MAX_OLD_RELEASES]

def refresh_cache():
    global cached_releases
    raw = fetch_releases()
    cached_releases = process_releases(raw)
    print(f"Cache updated: {len(cached_releases)} releases.")

def background_updater():
    while True:
        time.sleep(CACHE_REFRESH_MINUTES * 60)
        try:
            refresh_cache()
        except Exception as e:
            print("Updater error:", e)

@app.route("/api/releases")
def api_releases():
    return jsonify(cached_releases)

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            margin: 0;
            background: transparent;
            font-family: 'Segoe UI', sans-serif;
            overflow: hidden;
        }
        .widget {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: {{ widget_width }};
            background: {{ widget_bg }};
            color: white;
            padding: {{ widget_padding }};
            display: flex;
            flex-direction: column;
            gap: 12px;
            border-radius: {{ widget_border_radius }};
            box-shadow: {{ widget_box_shadow }};
            opacity: 0;
            transition: opacity {{ fade_duration/1000 }}s ease;
        }
        .widget.show { opacity: 1; }
        .flip-container {
            perspective: 1000px;
            width: 100%;
        }
        .flipper {
            transition: transform {{ flip_duration/1000 }}s;
            transform-style: preserve-3d;
            position: relative;
            width: 100%;
            aspect-ratio: {{ flipper_aspect_ratio }};
        }
        .flipper.flipped { transform: rotateY(180deg); }
        .front, .back {
            position: absolute;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            border-radius: {{ widget_border_radius }};
        }
        .front {
            background-size: {{ front_bg_size }};
            background-position: {{ front_bg_position }};
        }
        .back {
            transform: rotateY(180deg);
            background: {{ back_bg }};
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .back img {
            max-width: {{ qr_max_width }};
            max-height: {{ qr_max_height }};
            object-fit: {{ qr_object_fit }};
        }
        .info {
            display: flex;
            flex-direction: column;
            gap: {{ info_gap }};
            margin-top: 8px;
        }
        .text-block { display: flex; flex-direction: column; }
        .title {
            font-size: {{ title_font_size }};
            font-weight: {{ title_font_weight }};
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
        }
        .author {
            font-size: {{ author_font_size }};
            opacity: {{ author_opacity }};
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
        }
        .album {
            font-size: {{ album_font_size }};
            opacity: {{ album_opacity }};
            text-transform: {{ album_text_transform }};
            letter-spacing: {{ album_letter_spacing }};
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
        }
        .badge {
            background: {{ badge_bg }};
            color: {{ badge_color }};
            padding: {{ badge_padding }};
            border-radius: {{ badge_border_radius }};
            font-size: {{ badge_font_size }};
            font-weight: {{ badge_font_weight }};
            margin-top: 6px;
            display: inline-block;
            width: fit-content;
        }
        .error { color: white; text-align: center; }
    </style>
</head>
<body>
    <div class="widget show" id="card"></div>

    <script>
        // Конфигурация, переданная из Python
        const CONFIG = {
            qrSize: {{ qr_size }},
            switchInterval: {{ switch_interval }},
            flipDelay: {{ flip_delay }},
            flipDuration: {{ flip_duration }},
            fadeDuration: {{ fade_duration }},
            fadeDelayBeforeUpdate: {{ fade_delay_before_update }},
            showBadge: {{ show_badge|tojson }},
            badgeText: {{ badge_text|tojson }},
            enableBackFlip: {{ enable_back_flip|tojson }},
            backFlipDelay: {{ back_flip_delay }}
        };

        let releases = [];
        let currentIndex = 0;
        let flipTimer = null;
        let backFlipTimer = null;
        let switchTimer = null;
        let updateTimeout = null;

        async function load() {
            try {
                const res = await fetch('/api/releases');
                if (!res.ok) throw new Error('HTTP error ' + res.status);
                releases = await res.json();
                if (releases.length === 0) {
                    document.getElementById('card').innerHTML = '<div class="error">No releases found</div>';
                    return;
                }
                showRelease();
                switchTimer = setInterval(nextRelease, CONFIG.switchInterval);
            } catch (err) {
                document.getElementById('card').innerHTML = '<div class="error">Failed to load releases</div>';
                console.error(err);
            }
        }

        function showRelease() {
            const r = releases[currentIndex];
            const card = document.getElementById('card');
            const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=${CONFIG.qrSize}x${CONFIG.qrSize}&data=${encodeURIComponent('https://rls.hpsbassline.club/' + r.slug)}`;

            // Очищаем все таймеры, связанные с текущим показом
            if (flipTimer) clearTimeout(flipTimer);
            if (backFlipTimer) clearTimeout(backFlipTimer);
            if (updateTimeout) clearTimeout(updateTimeout);

            // Начинаем fade-out
            card.classList.remove('show');

            // После fade-out обновляем содержимое и делаем fade-in
            updateTimeout = setTimeout(() => {
                card.innerHTML = `
                    <div class="flip-container">
                        <div class="flipper" id="flipper">
                            <div class="front" style="background-image: url('${escapeHtml(r.cover)}');"></div>
                            <div class="back"><img src="${qrUrl}" alt="QR code"></div>
                        </div>
                    </div>
                    <div class="info">
                        <div class="text-block">
                            <div class="title">${escapeHtml(r.title)}</div>
                            <div class="author">${escapeHtml(r.author)}</div>
                            <div class="album">${escapeHtml(r.album)}</div>
                        </div>
                        ${CONFIG.showBadge && r.is_new ? `<div class="badge">${CONFIG.badgeText}</div>` : ''}
                    </div>
                `;
                card.classList.add('show');

                const flipper = document.getElementById('flipper');
                flipper.classList.remove('flipped'); // начинаем с лицевой стороны

                // Таймер для переворота на QR
                flipTimer = setTimeout(() => {
                    flipper.classList.add('flipped');

                    // Если включен обратный переворот, ставим таймер на возврат
                    if (CONFIG.enableBackFlip) {
                        backFlipTimer = setTimeout(() => {
                            flipper.classList.remove('flipped');
                        }, CONFIG.backFlipDelay);
                    }
                }, CONFIG.flipDelay);
            }, CONFIG.fadeDelayBeforeUpdate);
        }

        function nextRelease() {
            if (releases.length === 0) return;
            currentIndex = (currentIndex + 1) % releases.length;
            showRelease();
        }

        function escapeHtml(text) {
            if (!text) return '';
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        }

        load();

        window.addEventListener('beforeunload', () => {
            if (switchTimer) clearInterval(switchTimer);
            if (flipTimer) clearTimeout(flipTimer);
            if (backFlipTimer) clearTimeout(backFlipTimer);
            if (updateTimeout) clearTimeout(updateTimeout);
        });
    </script>
</body>
</html>
""",
        # Передаём все настройки в шаблон
        widget_width=WIDGET_WIDTH,
        widget_bg=WIDGET_BG,
        widget_blur=WIDGET_BLUR,
        widget_padding=WIDGET_PADDING,
        widget_border_radius=WIDGET_BORDER_RADIUS,
        widget_box_shadow=WIDGET_BOX_SHADOW,
        flipper_aspect_ratio=FLIPPER_ASPECT_RATIO,
        flip_duration=FLIP_DURATION,
        front_bg_size=FRONT_BG_SIZE,
        front_bg_position=FRONT_BG_POSITION,
        back_bg=BACK_BG,
        qr_max_width=QR_MAX_WIDTH,
        qr_max_height=QR_MAX_HEIGHT,
        qr_object_fit=QR_OBJECT_FIT,
        info_gap=INFO_GAP,
        title_font_size=TITLE_FONT_SIZE,
        title_font_weight=TITLE_FONT_WEIGHT,
        author_font_size=AUTHOR_FONT_SIZE,
        author_opacity=AUTHOR_OPACITY,
        album_font_size=ALBUM_FONT_SIZE,
        album_opacity=ALBUM_OPACITY,
        album_text_transform=ALBUM_TEXT_TRANSFORM,
        album_letter_spacing=ALBUM_LETTER_SPACING,
        badge_bg=BADGE_BG,
        badge_color=BADGE_COLOR,
        badge_padding=BADGE_PADDING,
        badge_border_radius=BADGE_BORDER_RADIUS,
        badge_font_size=BADGE_FONT_SIZE,
        badge_font_weight=BADGE_FONT_WEIGHT,
        # Числовые параметры
        qr_size=QR_SIZE,
        switch_interval=SWITCH_INTERVAL,
        flip_delay=FLIP_DELAY,
        fade_duration=FADE_DURATION,
        fade_delay_before_update=FADE_DELAY_BEFORE_UPDATE,
        show_badge=SHOW_BADGE,
        badge_text=BADGE_TEXT,
        enable_back_flip=ENABLE_BACK_FLIP,
        back_flip_delay=BACK_FLIP_DELAY
    )

if __name__ == "__main__":
    refresh_cache()
    thread = threading.Thread(target=background_updater, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=5000)