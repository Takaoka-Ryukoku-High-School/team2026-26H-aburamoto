import json
import random
import time
from collections import deque
from datetime import date
from pathlib import Path
from threading import Lock
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4

import flet as ft
from fastapi import FastAPI


DATA_FILE = Path.home() / ".daily_note_tasks.json"
GREEN = "#2E6654"
GREEN_LIGHT = "#E2EDE5"
PAPER = "#F6F5EF"
INK = "#202C2A"
MUTED = "#77807B"
CORAL = "#CF6048"
WEATHER_NOTIFICATIONS = deque(maxlen=50)
WEATHER_NOTIFICATIONS_LOCK = Lock()
WEATHER_NOTIFICATION_ID = 0

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


def make_weather_alert(weather):
    alerts = []
    if weather["rain"] >= 50 or weather["code"] >= 51:
        alerts.append(f"雨の予報です（降水確率 {weather['rain']}%）。傘を用意してください。")
    if weather["max"] >= 30:
        alerts.append(f"最高気温は{weather['max']:.0f}℃の予報です。水分補給と暑さ対策を。")
    wind_speed = weather["current"]["wind_speed_10m"]
    if wind_speed >= 35:
        alerts.append(f"現在の風速は{wind_speed:.0f} km/hです。屋外での活動に注意してください。")
    if not alerts:
        return None
    return {
        "title": f"{weather['city']}の天気に注意",
        "body": "\n".join(alerts),
    }


def enqueue_weather_notification(alert):
    global WEATHER_NOTIFICATION_ID
    with WEATHER_NOTIFICATIONS_LOCK:
        WEATHER_NOTIFICATION_ID += 1
        WEATHER_NOTIFICATIONS.append({
            "id": WEATHER_NOTIFICATION_ID,
            "created_at": int(time.time() * 1000),
            **alert,
        })


def make_recommendations(weather):
    categories = {
        "外出": [],
        "運動": [],
        "室内": [],
        "休憩": [],
        "体調管理": [],
        "持ち物": [],
        "安全": [],
    }

    def add(category, item, reason, period="いつでも"):
        if not any(recommendation["text"] == item for recommendation in categories[category]):
            categories[category].append({
                "kind": category,
                "text": item,
                "reason": reason,
                "period": period,
            })

    if weather["rain"] >= 50 or weather["code"] >= 51:
        rain_reason = (
            f"降水確率が{weather['rain']}%と高いため。"
            if weather["rain"] >= 50
            else "雨の予報が出ているため。"
        )
        add("持ち物", "折りたたみ傘をバッグに入れる", rain_reason, "朝")
        add("室内", "屋外の予定は短めにして、室内の時間を増やす", rain_reason)
        add("室内", "机まわりを5分だけ片付ける", rain_reason)
        add("外出", "近場の用事をまとめて、雨にぬれる時間を減らす", rain_reason, "昼")
        add("外出", "出かける際は、屋根のあるルートを選ぶ", rain_reason, "いつでも")
        add("運動", "室内で5分だけストレッチをする", rain_reason)
        add("運動", "好きな音楽に合わせて、室内で軽く体を動かす", rain_reason)
        add("休憩", "読書や映画など、雨の日にちょうどいいゆったり行動を選ぶ", rain_reason)
        add("休憩", "温かい飲み物を用意して一息つく", rain_reason)
    elif weather["max"] >= 28:
        heat_reason = f"最高気温が{weather['max']:.0f}℃の予報のため。"
        add("外出", "涼しい朝か夕方に散歩する", heat_reason, "朝")
        add("外出", "日陰のある道を選んで短時間歩く", heat_reason, "昼")
        add("運動", "涼しい時間帯に軽いウォーキングをする", heat_reason, "夕方・夜")
        add("運動", "室内で軽いストレッチをする", heat_reason)
        add("体調管理", "水分補給をこまめにして、日差しを避ける", heat_reason)
        add("持ち物", "帽子や水分の入ったボトルを持ち歩く", heat_reason, "朝")
        add("室内", "涼しい室内で読書や作業を進める", heat_reason)
        add("室内", "カーテンを閉めて、部屋に熱がこもるのを防ぐ", heat_reason, "昼")
        add("休憩", "涼しい場所で目を閉じて数分休む", heat_reason)
        add("休憩", "好きな音楽を聴きながら、無理せず休憩する", heat_reason)
    elif weather["max"] <= 10:
        cold_reason = f"最高気温が{weather['max']:.0f}℃と低い予報のため。"
        add("体調管理", "温かい飲み物を用意する", cold_reason, "朝")
        add("外出", "外出は短時間にして室内の用事を進める", cold_reason)
        add("外出", "日が出て暖かい時間帯に、近所を短く歩く", cold_reason, "昼")
        add("体調管理", "暖かい服装で、体を冷やしすぎないようにする", cold_reason, "朝")
        add("運動", "室内で軽いストレッチをして、体を温めておく", cold_reason)
        add("運動", "部屋の中で足踏みをして、少し体を動かす", cold_reason)
        add("室内", "温かい部屋で読書や勉強をする", cold_reason)
        add("室内", "座ってできる片付けや作業をひとつ進める", cold_reason)
        add("休憩", "温かい飲み物を飲みながら、ゆっくり休む", cold_reason)
    else:
        mild_reason = "極端な暑さや寒さの予報がなく、過ごしやすそうなため。"
        add("外出", "昼休みに15分だけ外を歩く", mild_reason, "昼")
        add("外出", "帰り道にいつもと違う道を歩いてみる", mild_reason, "夕方・夜")
        add("室内", "窓を開けて部屋の空気を入れ替える", mild_reason, "昼")
        add("室内", "机の上を5分だけ片付けて気分を整える", mild_reason)
        add("休憩", "少しだけ好きな音楽を聴いて気分転換する", mild_reason)
        add("休憩", "休憩中に深呼吸をして、目を閉じてひと休みする", mild_reason)
        add("運動", "肩や首をほぐす軽い体操をする", mild_reason)
        add("運動", "階段を使うか、短い散歩で軽く体を動かす", mild_reason)

    if weather["code"] in {0, 1} and 12 <= weather["max"] < 28:
        add("外出", "外でやりたかったことをひとつ実行する", "晴れの予報で、最高気温も過ごしやすい範囲のため。", "昼")
    if weather["current"]["wind_speed_10m"] >= 35:
        wind_speed = weather["current"]["wind_speed_10m"]
        add("安全", "風が強いので、自転車や屋外作業は控える", f"現在の風速が{wind_speed:.0f} km/hと強いため。")
    if weather["max"] >= 30:
        add("安全", "日差しが強いので、日焼け止めを塗ってから外に出る", f"最高気温が{weather['max']:.0f}℃の予報のため。", "朝")
    if 15 <= weather["max"] < 25 and weather["current"]["wind_speed_10m"] < 20:
        add("外出", "気持ちいい日なので、少し長めに散歩して気分を整える", "気温が15〜24℃で、風も比較的弱いため。", "昼")
    if weather["max"] <= 12:
        add("休憩", "静かに休んで、体を温めてから動く", f"最高気温が{weather['max']:.0f}℃と低い予報のため。", "夕方・夜")

    recommendations = []
    order = ["安全", "持ち物", "体調管理", "外出", "運動", "室内", "休憩"]
    for category in order:
        recommendations.extend(categories[category])

    return recommendations


def group_recommendations(recommendations, category_filter="すべて"):
    periods = ("朝", "昼", "夕方・夜", "いつでも")
    grouped = {period: [] for period in periods}
    for recommendation in recommendations:
        if category_filter != "すべて" and recommendation["kind"] != category_filter:
            continue
        period = recommendation.get("period", "いつでも")
        grouped.setdefault(period, []).append(recommendation)
    return [(period, grouped[period]) for period in periods if grouped[period]]


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
    recommendation_filter = "すべて"
    recommendations = []
    today = ft.Text(date.today().strftime("%Y年%m月%d日"), size=12, color=MUTED)
    city_input = ft.TextField(value="東京", label="場所", hint_text="例：東京都、大阪府、北海道、那覇", expand=True, border_radius=6, border_color="#D4DED5", focused_border_color=GREEN, bgcolor="#FFFEFA")
    weather_status = ft.Text("場所を選ぶと、今日の気候を確認できます", size=12, color=MUTED)
    weather_summary = ft.Column(spacing=4)
    day_advice_list = ft.Column(spacing=8)
    recommendation_filter_row = ft.Row(wrap=True, spacing=4, run_spacing=4)
    recommendation_list = ft.Column(spacing=8)
    task_input = ft.TextField(label="自分で追加", hint_text="例：夕方に散歩する", expand=True, border_radius=6, border_color="#D4DED5", focused_border_color=GREEN, bgcolor="#FFFEFA")
    task_list = ft.Column(spacing=0)
    task_count = ft.Text(color=MUTED, size=12)
    progress_label = ft.Text(color=MUTED, size=11)
    review_count = ft.Text(color=MUTED, size=11)
    review_list = ft.Column(spacing=4)
    clear_done_button = ft.TextButton("完了した行動を削除", icon=ft.Icons.DELETE_OUTLINE, style=ft.ButtonStyle(color=CORAL))
    quick_task_suggestions = [
        "10分だけ散歩する",
        "ストレッチをする",
        "水分をたくさん取る",
        "部屋を少し片付ける",
        "好きな音楽を1曲聴く",
        "15分だけ外を歩く",
        "軽い体操をする",
        "今日は少しゆっくり休む",
        "窓を開けて気分転換する",
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
        completed_tasks = [task for task in tasks if task["done"]]
        completed = len(completed_tasks)
        task_count.value = f"未完了 {len(tasks) - completed} 件"
        progress_label.value = f"{completed} / {len(tasks)} 件 完了" if tasks else "提案をチェックリストに追加できます"
        review_count.value = f"{completed} 件完了"
        review_list.controls = [
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=GREEN, size=16),
                ft.Text(task["text"], color=INK, size=13, expand=True),
            ], spacing=8)
            for task in completed_tasks
        ] or [ft.Text("完了した行動はここに表示されます", color=MUTED, size=12)]
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

    def set_recommendation_filter(value):
        nonlocal recommendation_filter
        recommendation_filter = value
        render_recommendations()

    def shuffle_recommendations(event):
        random.shuffle(recommendations)
        render_recommendations()

    def render_recommendations():
        categories = list(dict.fromkeys(item["kind"] for item in recommendations))
        filter_options = ["すべて", *categories]
        if recommendation_filter not in filter_options:
            set_recommendation_filter("すべて")
            return
        recommendation_filter_row.controls = [
            ft.TextButton(
                category,
                on_click=lambda event, value=category: set_recommendation_filter(value),
                style=ft.ButtonStyle(
                    color=GREEN if category == recommendation_filter else MUTED,
                    bgcolor=GREEN_LIGHT if category == recommendation_filter else "transparent",
                    shape=ft.RoundedRectangleBorder(radius=16),
                ),
            )
            for category in filter_options
        ]

        recommendation_list.controls = []
        for period, items in group_recommendations(recommendations, recommendation_filter):
            recommendation_list.controls.append(
                ft.Text(period, size=13, color=GREEN, weight=ft.FontWeight.BOLD)
            )
            for recommendation in items:
                label = recommendation["kind"]
                text = recommendation["text"]
                reason = recommendation["reason"]
                recommendation_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Text(label, size=10, weight=ft.FontWeight.BOLD, color=GREEN),
                                padding=ft.Padding.all(6),
                                bgcolor=GREEN_LIGHT,
                                border_radius=12,
                            ),
                            ft.Column([
                                ft.Text(text, color=INK, size=14),
                                ft.Text(f"理由：{reason}", color=MUTED, size=11),
                            ], spacing=3, expand=True),
                            ft.TextButton("追加", on_click=lambda event, value=text: add_task(value)),
                        ], spacing=8, alignment=ft.MainAxisAlignment.START),
                        padding=8,
                        border=ft.Border.all(1, "#E3E3D9"),
                        border_radius=8,
                        bgcolor="#FFFEFA",
                    )
                )
        if not recommendation_list.controls:
            recommendation_list.controls.append(
                ft.Text("このカテゴリの提案はありません", color=MUTED, size=12)
            )
        page.update()

    def show_weather(data):
        nonlocal recommendations, recommendation_filter
        recommendation_filter = "すべて"
        recommendations = make_recommendations(data)
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
        render_recommendations()

    def update_weather():
        city = city_input.value.strip()
        if not city:
            weather_status.value = "場所を入力してください"
            page.update()
            return
        weather_status.value = "天気を確認しています..."
        page.update()
        try:
            weather = fetch_weather(city)
            show_weather(weather)
            alert = make_weather_alert(weather)
            if alert:
                enqueue_weather_notification(alert)
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
        recommendation_filter_row,
        ft.Row([
            ft.TextButton(
                "提案をシャッフル",
                icon=ft.Icons.SHUFFLE,
                on_click=shuffle_recommendations,
                style=ft.ButtonStyle(color=GREEN),
            ),
        ], alignment=ft.MainAxisAlignment.END),
        recommendation_list,
    ], spacing=14), padding=20, bgcolor="#FFFEFA", border=ft.Border.all(1, "#E3E3D9"), border_radius=8)
    checklist_panel = ft.Container(content=ft.Column([
        ft.Text("今日やること", size=18, color=INK, weight=ft.FontWeight.BOLD),
        ft.Row([task_input, ft.Button("追加  ＋", on_click=lambda event: add_task(), bgcolor=GREEN, color="white", height=48)], spacing=10),
        ft.Text("すぐ追加できる候補", size=12, color=MUTED),
        quick_task_row,
        ft.Row([ft.Row(list(filter_buttons.values()), spacing=0), task_count], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        task_list,
        ft.Container(content=ft.Column([
            ft.Row([
                ft.Text("完了した行動を振り返る", size=14, color=INK, weight=ft.FontWeight.BOLD),
                review_count,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            review_list,
        ], spacing=8), padding=12, bgcolor=GREEN_LIGHT, border_radius=8),
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


def create_web_app():
    flet_app = ft.run(
        main,
        export_asgi_app=True,
        assets_dir=str(Path(__file__).parent / "assets"),
    )
    web_app = FastAPI()

    @web_app.get("/api/weather-notifications")
    def get_weather_notifications(after: int = 0):
        with WEATHER_NOTIFICATIONS_LOCK:
            notifications = [
                notification
                for notification in WEATHER_NOTIFICATIONS
                if notification["id"] > after
            ]
        return {"notifications": notifications}

    web_app.mount("/", flet_app)
    return web_app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_web_app(), host="0.0.0.0", port=8000)
