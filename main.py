import json
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4

import flet as ft


DATA_FILE = Path.home() / ".daily_note_tasks.json"
GREEN = "#2E6654"
GREEN_LIGHT = "#E2EDE5"
PAPER = "#F6F5EF"
INK = "#202C2A"
MUTED = "#77807B"
CORAL = "#CF6048"

WEATHER_LABELS = {
    0: ("快晴", "☀"), 1: ("晴れ", "☀"), 2: ("晴れ時々くもり", "⛅"), 3: ("くもり", "☁"),
    45: ("霧", "🌫"), 48: ("霧", "🌫"), 51: ("弱い霧雨", "🌦"), 53: ("霧雨", "🌦"),
    55: ("強い霧雨", "🌧"), 61: ("弱い雨", "🌦"), 63: ("雨", "🌧"), 65: ("強い雨", "🌧"),
    71: ("弱い雪", "🌨"), 73: ("雪", "❄"), 75: ("強い雪", "❄"), 80: ("にわか雨", "🌦"),
    81: ("にわか雨", "🌧"), 82: ("激しいにわか雨", "🌧"), 95: ("雷雨", "⛈"),
    96: ("雷雨とひょう", "⛈"), 99: ("雷雨とひょう", "⛈"),
}

CITY_ALIASES = {
    "東京": "Tokyo",
    "大阪": "Osaka",
    "札幌": "Sapporo",
    "名古屋": "Nagoya",
    "福岡": "Fukuoka",
    "横浜": "Yokohama",
    "京都": "Kyoto",
    "神戸": "Kobe",
    "仙台": "Sendai",
    "広島": "Hiroshima",
    "那覇": "Naha",
}

PREFECTURE_CITIES = {
    "北海道": "Sapporo",
    "青森県": "Aomori",
    "岩手県": "Morioka",
    "宮城県": "Sendai",
    "秋田県": "Akita",
    "山形県": "Yamagata",
    "福島県": "Fukushima",
    "茨城県": "Mito",
    "栃木県": "Utsunomiya",
    "群馬県": "Maebashi",
    "埼玉県": "Saitama",
    "千葉県": "Chiba",
    "東京都": "Tokyo",
    "神奈川県": "Yokohama",
    "新潟県": "Niigata",
    "富山県": "Toyama",
    "石川県": "Kanazawa",
    "福井県": "Fukui",
    "山梨県": "Kofu",
    "長野県": "Nagano",
    "岐阜県": "Gifu",
    "静岡県": "Shizuoka",
    "愛知県": "Nagoya",
    "三重県": "Tsu",
    "滋賀県": "Otsu",
    "京都府": "Kyoto",
    "大阪府": "Osaka",
    "兵庫県": "Kobe",
    "奈良県": "Nara",
    "和歌山県": "Wakayama",
    "鳥取県": "Tottori",
    "島根県": "Matsue",
    "岡山県": "Okayama",
    "広島県": "Hiroshima",
    "山口県": "Yamaguchi",
    "徳島県": "Tokushima",
    "香川県": "Takamatsu",
    "愛媛県": "Matsuyama",
    "高知県": "Kochi",
    "福岡県": "Fukuoka",
    "佐賀県": "Saga",
    "長崎県": "Nagasaki",
    "熊本県": "Kumamoto",
    "大分県": "Oita",
    "宮崎県": "Miyazaki",
    "鹿児島県": "Kagoshima",
    "沖縄県": "Naha",
}

PREFECTURE_ALIASES = {
    name: city
    for prefecture, city in PREFECTURE_CITIES.items()
    for name in (
        (prefecture, prefecture[:-1])
        if prefecture.endswith(("都", "府", "県"))
        else (prefecture,)
    )
}


def resolve_place_name(city):
    value = (city or "").strip()
    if not value:
        return value

    alias = CITY_ALIASES.get(value)
    if alias:
        return alias

    prefecture_alias = PREFECTURE_ALIASES.get(value)
    if prefecture_alias:
        return prefecture_alias

    for suffix in ("都", "道", "府", "県"):
        if value.endswith(suffix):
            stripped = value[:-1]
            alias = CITY_ALIASES.get(stripped)
            if alias:
                return alias
            prefecture_alias = PREFECTURE_ALIASES.get(stripped)
            if prefecture_alias:
                return prefecture_alias

    return value


def load_tasks():
    try:
        tasks = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(tasks, list):
            return [
                task for task in tasks
                if isinstance(task, dict)
                and isinstance(task.get("id"), str)
                and isinstance(task.get("text"), str)
                and isinstance(task.get("done"), bool)
            ]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_tasks(tasks):
    DATA_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_weather(city):
    place_name = (city or "").strip()
    search_name = resolve_place_name(place_name)
    geocoding_params = {"name": search_name, "count": 1, "language": "en", "format": "json"}
    if place_name in PREFECTURE_ALIASES:
        geocoding_params["countryCode"] = "JP"
    query = urlencode(geocoding_params)
    with urlopen(f"https://geocoding-api.open-meteo.com/v1/search?{query}", timeout=10) as response:
        locations = json.loads(response.read().decode("utf-8")).get("results", [])
    if not locations:
        raise ValueError("その場所は見つかりませんでした")

    location = locations[0]
    query = urlencode({
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,precipitation_probability,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "timezone": "auto",
        "forecast_days": 1,
    })
    with urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=10) as response:
        forecast = json.loads(response.read().decode("utf-8"))

    daily = forecast["daily"]
    return {
        "city": location["name"],
        "country": location.get("country", ""),
        "current": forecast["current"],
        "hourly": forecast["hourly"],
        "max": daily["temperature_2m_max"][0],
        "min": daily["temperature_2m_min"][0],
        "rain": daily["precipitation_probability_max"][0] or 0,
        "code": daily["weather_code"][0],
    }


def make_recommendations(weather):
    if weather["rain"] >= 50 or weather["code"] >= 51:
        recommendations = ["折りたたみ傘をバッグに入れる", "読書や映画など、室内の時間をつくる"]
    elif weather["max"] >= 28:
        recommendations = ["午前中か夕方に散歩する", "水分補給をこまめにする"]
    elif weather["max"] <= 10:
        recommendations = ["温かい飲み物を用意する", "外出は短時間にして室内の用事を進める"]
    else:
        recommendations = ["昼休みに15分だけ外を歩く", "窓を開けて部屋の空気を入れ替える"]

    if weather["code"] in {0, 1} and 12 <= weather["max"] < 28:
        recommendations.insert(0, "外でやりたかったことをひとつ実行する")
    if weather["current"]["wind_speed_10m"] >= 35:
        recommendations.append("風が強いので、自転車や屋外作業は控える")
    return recommendations[:3]


def make_day_advice(hourly):
    periods = (("朝", 6, 12), ("昼", 12, 18), ("夕方・夜", 18, 24))
    advice = []
    for label, start_hour, end_hour in periods:
        forecast = [
            (temperature, rain, code, wind)
            for time, temperature, rain, code, wind in zip(
                hourly["time"],
                hourly["temperature_2m"],
                hourly["precipitation_probability"],
                hourly["weather_code"],
                hourly["wind_speed_10m"],
            )
            if start_hour <= int(time[11:13]) < end_hour
        ]
        if not forecast:
            continue

        temperatures = [item[0] for item in forecast]
        rain = max(item[1] or 0 for item in forecast)
        codes = [item[2] for item in forecast]
        wind = max(item[3] for item in forecast)

        if rain >= 50 or any(code >= 51 for code in codes):
            tip = "雨具を用意して、屋外の予定は短めに。"
        elif max(temperatures) >= 28:
            tip = "暑さに注意して水分補給を。外出は涼しい時間帯に。"
        elif min(temperatures) <= 10:
            tip = "冷え込みに備えて、暖かい上着を用意しましょう。"
        elif wind >= 35:
            tip = "風が強まりそうです。自転車や屋外作業に注意を。"
        elif all(code in {0, 1} for code in codes) and 12 <= max(temperatures) < 28:
            tip = "晴れて過ごしやすそうです。散歩など屋外の予定におすすめ。"
        else:
            tip = "天候の変化に備えて、予定に余裕を持ちましょう。"

        advice.append({
            "period": label,
            "min": min(temperatures),
            "max": max(temperatures),
            "rain": rain,
            "tip": tip,
        })
    return advice


def main(page: ft.Page):
    page.title = "今日の気候で決める | DAILY NOTE"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = PAPER
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    tasks = load_tasks()
    current_filter = "all"
    today = ft.Text(date.today().strftime("%Y年%m月%d日"), size=12, color=MUTED)
    city_input = ft.TextField(value="東京", label="場所", hint_text="例：東京都、大阪府、北海道、那覇", expand=True, border_radius=6, border_color="#D4DED5", focused_border_color=GREEN, bgcolor="#FFFEFA")
    weather_status = ft.Text("場所を選ぶと、今日の気候を確認できます", size=12, color=MUTED)
    weather_summary = ft.Column(spacing=4)
    day_advice_list = ft.Column(spacing=8)
    recommendation_list = ft.Column(spacing=8)
    task_input = ft.TextField(label="自分で追加", hint_text="例：夕方に散歩する", expand=True, border_radius=6, border_color="#D4DED5", focused_border_color=GREEN, bgcolor="#FFFEFA")
    task_list = ft.Column(spacing=0)
    task_count = ft.Text(color=MUTED, size=12)
    progress_label = ft.Text(color=MUTED, size=11)
    clear_done_button = ft.TextButton("完了した行動を削除", icon=ft.Icons.DELETE_OUTLINE, style=ft.ButtonStyle(color=CORAL))
    quick_task_suggestions = [
        "10分だけ散歩する",
        "ストレッチをする",
        "水分をたくさん取る",
        "部屋を少し片付ける",
        "好きな音楽を1曲聴く",
    ]
    quick_task_row = ft.Row(wrap=True, spacing=6, run_spacing=6)
    filter_buttons = {}

    def persist():
        try:
            save_tasks(tasks)
        except OSError:
            progress_label.value = "保存できませんでした。書き込み権限をご確認ください。"

    def add_task(text=None):
        value = (text if text is not None else task_input.value).strip()
        if not value:
            return
        normalized = " ".join(value.split())
        if any(task["text"] == normalized for task in tasks):
            task_input.value = ""
            progress_label.value = "同じ行動はすでに追加済みです。"
            page.update()
            return
        tasks.insert(0, {"id": str(uuid4()), "text": normalized, "done": False})
        task_input.value = ""
        progress_label.value = "行動を追加しました。"
        persist()
        render_tasks()

    def render_quick_tasks():
        quick_task_row.controls = [
            ft.TextButton(
                suggestion,
                on_click=lambda event, value=suggestion: add_task(value),
                style=ft.ButtonStyle(color=GREEN, bgcolor=GREEN_LIGHT, shape=ft.RoundedRectangleBorder(radius=18)),
            )
            for suggestion in quick_task_suggestions
        ]
        page.update()

    def toggle_task(task_id):
        for task in tasks:
            if task["id"] == task_id:
                task["done"] = not task["done"]
                break
        persist()
        render_tasks()

    def delete_task(task_id):
        tasks[:] = [task for task in tasks if task["id"] != task_id]
        persist()
        render_tasks()

    def clear_done():
        tasks[:] = [task for task in tasks if not task["done"]]
        persist()
        render_tasks()

    def set_filter(value):
        nonlocal current_filter
        current_filter = value
        render_tasks()

    def render_tasks():
        visible_tasks = [task for task in tasks if current_filter == "all" or (current_filter == "active" and not task["done"]) or (current_filter == "done" and task["done"])]
        completed = sum(task["done"] for task in tasks)
        task_count.value = f"未完了 {len(tasks) - completed} 件"
        progress_label.value = f"{completed} / {len(tasks)} 件 完了" if tasks else "提案をチェックリストに追加できます"
        clear_done_button.visible = completed > 0
        for key, button in filter_buttons.items():
            selected = key == current_filter
            button.style = ft.ButtonStyle(color=GREEN if selected else MUTED, bgcolor=GREEN_LIGHT if selected else "transparent", shape=ft.RoundedRectangleBorder(radius=4))

        rows = []
        for task in visible_tasks:
            checkbox = ft.Checkbox(value=task["done"], label=task["text"], expand=True, active_color=GREEN, label_style=ft.TextStyle(color="#929992" if task["done"] else INK, decoration=ft.TextDecoration.LINE_THROUGH if task["done"] else None, size=14), on_change=lambda event, task_id=task["id"]: toggle_task(task_id))
            rows.extend([ft.Row([checkbox, ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=MUTED, tooltip=f"「{task['text']}」を削除", on_click=lambda event, task_id=task["id"]: delete_task(task_id))], spacing=8), ft.Divider(height=1, thickness=1, color="#DEDFD5")])
        if not visible_tasks:
            rows = [ft.Container(content=ft.Text("ここに今日の行動が並びます", size=13, color=MUTED, text_align=ft.TextAlign.CENTER), padding=28, alignment=ft.Alignment.CENTER)]
        task_list.controls = rows
        page.update()

    def show_weather(data):
        label, icon = WEATHER_LABELS.get(data["code"], ("天候", "☁"))
        weather_status.value = f"{data['city']} / {data['country']} の今日の予報"
        weather_summary.controls = [ft.Row([ft.Text(icon, size=42), ft.Column([ft.Text(label, size=20, color=INK, weight=ft.FontWeight.BOLD), ft.Text(f"現在 {data['current']['temperature_2m']:.0f}°C  ·  最高 {data['max']:.0f}°C / 最低 {data['min']:.0f}°C", color=MUTED, size=13), ft.Text(f"降水確率 {data['rain']}%  ·  風速 {data['current']['wind_speed_10m']:.0f} km/h", color=MUTED, size=12)], spacing=4)], spacing=16)]
        day_advice_list.controls = [
            ft.Container(
                content=ft.Row([
                    ft.Text(item["period"], width=64, color=GREEN, weight=ft.FontWeight.BOLD),
                    ft.Column([
                        ft.Text(f"{item['min']:.0f}〜{item['max']:.0f}°C  ·  降水確率 最大 {item['rain']}%", size=12, color=MUTED),
                        ft.Text(item["tip"], size=13, color=INK),
                    ], spacing=4, expand=True),
                ], spacing=10),
                padding=10,
                bgcolor=GREEN_LIGHT,
                border_radius=6,
            )
            for item in make_day_advice(data["hourly"])
        ]
        recommendation_list.controls = [ft.Row([ft.Text("✓", color=GREEN, size=17, weight=ft.FontWeight.BOLD), ft.Text(recommendation, color=INK, size=14, expand=True), ft.TextButton("追加", on_click=lambda event, value=recommendation: add_task(value))], spacing=8) for recommendation in make_recommendations(data)]
        page.update()

    def update_weather():
        city = city_input.value.strip()
        if not city:
            weather_status.value = "場所を入力してください"
            page.update()
            return
        weather_status.value = "天気を確認しています..."
        page.update()
        try:
            show_weather(fetch_weather(city))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            weather_status.value = "天気を取得できませんでした。場所名を変えて試してください。"
            page.update()

    city_input.on_submit = lambda event: update_weather()
    task_input.on_submit = lambda event: add_task()
    clear_done_button.on_click = lambda event: clear_done()
    for key, label in (("all", "すべて"), ("active", "未完了"), ("done", "完了")):
        filter_buttons[key] = ft.TextButton(label, on_click=lambda event, value=key: set_filter(value))

    weather_panel = ft.Container(content=ft.Column([
        ft.Row([ft.Text("今日の気候", size=18, color=INK, weight=ft.FontWeight.BOLD), ft.Text("行動のヒント", size=12, color=GREEN)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Row([city_input, ft.Button("天気を見る", on_click=lambda event: update_weather(), bgcolor=GREEN, color="white", height=48)], spacing=10),
        weather_status, weather_summary,
        ft.Text("一日のアドバイス", size=14, color=INK, weight=ft.FontWeight.BOLD),
        day_advice_list,
        ft.Text("今日の行動ヒント", size=14, color=INK, weight=ft.FontWeight.BOLD),
        recommendation_list,
    ], spacing=14), padding=20, bgcolor="#FFFEFA", border=ft.Border.all(1, "#E3E3D9"), border_radius=8)
    checklist_panel = ft.Container(content=ft.Column([
        ft.Text("今日やること", size=18, color=INK, weight=ft.FontWeight.BOLD),
        ft.Row([task_input, ft.Button("追加  ＋", on_click=lambda event: add_task(), bgcolor=GREEN, color="white", height=48)], spacing=10),
        ft.Text("すぐ追加できる候補", size=12, color=MUTED),
        quick_task_row,
        ft.Row([ft.Row(list(filter_buttons.values()), spacing=0), task_count], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        task_list,
        ft.Row([progress_label, clear_done_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
    ], spacing=12), padding=20, bgcolor="#FFFEFA", border=ft.Border.all(1, "#E3E3D9"), border_radius=8)

    content = ft.Column([
        ft.Row([ft.Row([ft.Container(content=ft.Text("天", color="white", size=15, weight=ft.FontWeight.BOLD), width=28, height=28, bgcolor=GREEN, border_radius=14, alignment=ft.Alignment.CENTER), ft.Text("DAILY NOTE", size=12, color=GREEN, weight=ft.FontWeight.BOLD)], spacing=10), today], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Column([ft.Text("気候で決める、今日の行動", size=34, color=INK, weight=ft.FontWeight.W_600), ft.Text("今日の空模様に合わせて、無理なく過ごし方を選ぼう。", size=13, color=MUTED)], spacing=4),
        weather_panel,
        checklist_panel,
    ], width=700, spacing=22)
    app_container = ft.Container(content=content, width=700, padding=ft.Padding.only(top=18, bottom=32))

    def resize_page(event):
        viewport_width = page.width or 748
        page.padding = 12 if viewport_width < 520 else 24
        content.width = min(700, max(272, viewport_width - page.padding * 2))
        app_container.width = content.width
        page.update()

    page.on_resize = resize_page
    page.add(app_container)
    render_quick_tasks()
    render_tasks()
    update_weather()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
