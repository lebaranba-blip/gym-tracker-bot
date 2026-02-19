import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
DATA_FILE = "gym_data.json"

# ═══════════════════════════════════════════════
# ПЛАНЫ ТРЕНИРОВОК
# ═══════════════════════════════════════════════

WORKOUT_PLANS = {
    "dima": {
        "name": "Дима 💪",
        "total_days": 3,
        "rotation": [1, 2, 3],
        "days": {
            1: {
                "title": "📅 День 1: ТОЛКАЙ (Грудь, Плечи, Трицепс)",
                "exercises": [
                    {"name": "Жим груди сидя (Matrix)", "sets": "3 x 8-10"},
                    {"name": "Жим на плечи сидя (Matrix)", "sets": "3 x 10-12"},
                    {"name": "Разведение гантелей в стороны (Махи)", "sets": "4 x 15"},
                    {"name": "Сведения рук «Бабочка»", "sets": "3 x 12-15"},
                    {"name": "Разгибания на трицепс (Канат)", "sets": "3 x 12-15"},
                ],
                "cardio": "🏃 Кардио: 15–20 мин (ходьба в горку)"
            },
            2: {
                "title": "📅 День 2: ТЯНИ (Спина, Бицепс)",
                "exercises": [
                    {"name": "Вертикальная тяга к груди (Matrix)", "sets": "3 x 8-12"},
                    {"name": "Горизонтальная тяга к животу (Matrix)", "sets": "3 x 10-12"},
                    {"name": "Тяга гантелей в наклоне", "sets": "3 x 10-12"},
                    {"name": "Сгибания на бицепс (Matrix)", "sets": "3 x 12-15"},
                    {"name": "«Молотки» с гантелями", "sets": "3 x 12"},
                ],
                "cardio": "🏃 Кардио: 15–20 мин (эллипс или гребля)"
            },
            3: {
                "title": "📅 День 3: НОГИ",
                "exercises": [
                    {"name": "Гак-приседания (Matrix)", "sets": "3 x 10"},
                    {"name": "Жим ногами — узко/низко (квадрицепс)", "sets": "3 x 10-12"},
                    {"name": "Жим ногами — широко/высоко (ягодицы)", "sets": "3 x 10-12"},
                    {"name": "Разгибания ног сидя (Matrix)", "sets": "3 x 12-15"},
                    {"name": "Сведение ног (Matrix)", "sets": "3 x 15"},
                ],
                "cardio": "🏃 Кардио: 15 мин спокойной ходьбы"
            }
        }
    },
    "ulyana": {
        "name": "Ульяна 🔥",
        "total_days": 4,
        "rotation": [1, 3, 2, 3],  # Низ А, Верх А, Низ Б, Верх А
        "days": {
            1: {
                "title": "🟣 НИЗ А — Ягодицы + Заднее бедро",
                "exercises": [
                    {"name": "Ягодичный мост (тренажёр)", "sets": "5 x 18-20"},
                    {"name": "Румынская тяга (гантели/штанга)", "sets": "4 x 13-15"},
                    {"name": "Выпады назад / болгарские", "sets": "4 x 14-15"},
                    {"name": "Сгибание ног лёжа", "sets": "3 x 12-14"},
                    {"name": "Отведение ноги назад в кроссовере", "sets": "3 подхода"},
                    {"name": "Гиперэкстензия (упор ягодицы)", "sets": "3 x 14-15"},
                    {"name": "Пресс (суперсет)", "sets": "скруч. + планка + скруч. с весом"},
                ],
                "cardio": ""
            },
            2: {
                "title": "🟣 НИЗ Б — Ягодицы (Верх + Бока)",
                "exercises": [
                    {"name": "Ягодичный мост с паузой", "sets": "5 x 12-18"},
                    {"name": "Выпады назад с гантелей / болгарские", "sets": "3 x 10"},
                    {"name": "Жим ногами (высокая постановка)", "sets": "4 x 12-15"},
                    {"name": "Отведение ног в тренажёре (манжеты)", "sets": "3 x 10-13"},
                    {"name": "Разведения ног сидя", "sets": "3 x 15-17"},
                    {"name": "Гиперэкстензия (узкая постановка)", "sets": "4 x 12"},
                ],
                "cardio": ""
            },
            3: {
                "title": "🔵 ВЕРХ А — Спина + Задняя/Средняя дельта",
                "exercises": [
                    {"name": "Тяга вертикального блока (к груди)", "sets": "4 x 11-16"},
                    {"name": "Тяга горизонтального блока", "sets": "4 x 11-13"},
                    {"name": "Тяга верхнего блока узким хватом", "sets": "3 x 12-15"},
                    {"name": "Разведение назад в кроссовере (задняя дельта)", "sets": "3 x 12-15"},
                    {"name": "Махи гантелями в стороны", "sets": "4 x 12-15"},
                    {"name": "Передняя дельта (махи вперёд)", "sets": "4 x 12"},
                    {"name": "Протяжка", "sets": "4 x 12-15"},
                    {"name": "Пресс", "sets": "3 подхода"},
                ],
                "cardio": ""
            },
            4: {
                "title": "🔵 ВЕРХ Б — Плечи + Грудь",
                "exercises": [
                    {"name": "Жим гантелей лёжа под углом 30-35°", "sets": "4 x 10-11"},
                    {"name": "Жим сидя вверх", "sets": "4 x 9-16"},
                    {"name": "Разведение гантелей в стороны", "sets": "4 x 12-13"},
                    {"name": "Трицепс в кроссовере", "sets": "4 x 9-15"},
                    {"name": "Передняя дельта (выведение вперёд)", "sets": "4 x 11-13"},
                    {"name": "Гравитрон", "sets": "4 x 11-12"},
                    {"name": "Отжимание от колен", "sets": "8-10"},
                    {"name": "Пресс", "sets": "3 подхода"},
                ],
                "cardio": ""
            }
        }
    }
}

# ═══════════════════════════════════════════════
# ХРАНЕНИЕ ДАННЫХ
# ═══════════════════════════════════════════════

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "plan": "dima",
            "weight_log": [],
            "workout_log": [],
            "next_day": 1
        }
        save_data(data)
    return data, uid

# ═══════════════════════════════════════════════
# КОМАНДЫ БОТА
# ═══════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"🏋️ *Gym Tracker Bot*\n"
        f"Привет, {user.first_name}!\n"
        f"Создатель: Дима\n\n"
        f"Команды:\n"
        f"/today — Тренировка на сегодня\n"
        f"/day1 — Толкай (Грудь, Плечи, Трицепс)\n"
        f"/day2 — Тяни (Спина, Бицепс)\n"
        f"/day3 — Ноги\n"
        f"/done — Записать тренировку ✅\n"
        f"/weight 84 — Записать вес\n"
        f"/progress — История веса 📊\n"
        f"/history — Журнал тренировок\n"
        f"/plan — Выбрать план тренировок"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

def format_workout(day_num, plan_key="ruslan"):
    plan = WORKOUT_PLANS[plan_key]["days"][day_num]
    lines = [f"*{plan['title']}*\n"]
    for i, ex in enumerate(plan["exercises"], 1):
        lines.append(f"{i}. {ex['name']} — *{ex['sets']}*")
    lines.append(f"\n{plan['cardio']}")
    return "\n".join(lines)

async def show_day(update: Update, context: ContextTypes.DEFAULT_TYPE, day: int):
    data, uid = get_user_data(update.effective_user.id)
    plan_key = data[uid].get("plan", "dima")
    if plan_key not in WORKOUT_PLANS:
        plan_key = "dima"
    text = format_workout(day, plan_key)
    keyboard = [[InlineKeyboardButton(f"✅ Записать тренировку", callback_data=f"done_{day}")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def day1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_day(update, context, 1)

async def day2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_day(update, context, 2)

async def day3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_day(update, context, 3)

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, uid = get_user_data(update.effective_user.id)
    next_day = data[uid].get("next_day", 1)
    await show_day(update, context, next_day)

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, uid = get_user_data(update.effective_user.id)
    plan_key = data[uid].get("plan", "dima")
    if plan_key not in WORKOUT_PLANS:
        plan_key = "dima"
    plan = WORKOUT_PLANS[plan_key]
    keyboard = []
    for day_num, day_data in plan["days"].items():
        title = day_data["title"]
        keyboard.append([InlineKeyboardButton(title, callback_data=f"done_{day_num}")])

    await update.message.reply_text(
        "Какую тренировку завершил(а)?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    day = int(query.data.split("_")[1])
    data, uid = get_user_data(query.from_user.id)

    plan_key = data[uid].get("plan", "dima")
    if plan_key not in WORKOUT_PLANS:
        plan_key = "dima"
    plan = WORKOUT_PLANS[plan_key]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    day_title = plan["days"][day]["title"]

    data[uid]["workout_log"].append({
        "day": day,
        "name": day_title,
        "date": now
    })

    # Следующий день по ротации
    rotation = plan.get("rotation", list(plan["days"].keys()))
    current_idx = data[uid].get("rotation_idx", 0)
    next_idx = (current_idx + 1) % len(rotation)
    data[uid]["rotation_idx"] = next_idx
    next_day = rotation[next_idx]
    data[uid]["next_day"] = next_day
    save_data(data)

    total = len(data[uid]["workout_log"])
    next_title = plan["days"][next_day]["title"]

    await query.edit_message_text(
        f"✅ *Тренировка записана!*\n\n"
        f"📅 {day_title}\n"
        f"🕐 {now}\n"
        f"📊 Всего тренировок: *{total}*\n\n"
        f"➡️ Следующая: {next_title}",
        parse_mode="Markdown"
    )

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи вес: `/weight 84.5`", parse_mode="Markdown")
        return

    try:
        w = float(context.args[0].replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Введи число, например: `/weight 84.5`", parse_mode="Markdown")
        return

    data, uid = get_user_data(update.effective_user.id)
    now = datetime.now().strftime("%Y-%m-%d")

    data[uid]["weight_log"].append({"weight": w, "date": now})
    save_data(data)

    logs = data[uid]["weight_log"]
    text = f"✅ Вес записан: *{w} кг*\n📅 {now}\n"

    if len(logs) >= 2:
        first = logs[0]["weight"]
        diff = w - first
        emoji = "📉" if diff < 0 else "📈" if diff > 0 else "➡️"
        text += f"\n{emoji} С начала: *{diff:+.1f} кг* (было {first} кг)"

    await update.message.reply_text(text, parse_mode="Markdown")

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, uid = get_user_data(update.effective_user.id)
    logs = data[uid].get("weight_log", [])

    if not logs:
        await update.message.reply_text("Пока нет записей. Введи вес: `/weight 85`", parse_mode="Markdown")
        return

    text = "📊 *История веса:*\n\n"
    for entry in logs[-15:]:  # Последние 15 записей
        text += f"📅 {entry['date']} — *{entry['weight']} кг*\n"

    first = logs[0]["weight"]
    last = logs[-1]["weight"]
    diff = last - first
    emoji = "📉" if diff < 0 else "📈" if diff > 0 else "➡️"

    bar_len = 20
    if first != last:
        progress_pct = min(abs(diff) / first * 100, 100)
        filled = int(bar_len * progress_pct / 100)
    else:
        filled = 0
    bar = "█" * filled + "░" * (bar_len - filled)

    text += f"\n{emoji} Итого: *{diff:+.1f} кг*\n"
    text += f"[{bar}] {abs(diff):.1f} кг сброшено" if diff < 0 else f"[{bar}]"

    await update.message.reply_text(text, parse_mode="Markdown")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, uid = get_user_data(update.effective_user.id)
    logs = data[uid].get("workout_log", [])

    if not logs:
        await update.message.reply_text("Пока нет тренировок. Сходи в зал! 💪")
        return

    text = "📋 *Журнал тренировок:*\n\n"
    for entry in logs[-10:]:
        text += f"📅 {entry['date']} — *{entry['name']}*\n"

    text += f"\n📊 Всего тренировок: *{len(logs)}*"

    # Статистика по типам
    day_counts = {}
    for entry in logs:
        name = entry["name"]
        day_counts[name] = day_counts.get(name, 0) + 1

    text += "\n"
    for name, count in day_counts.items():
        text += f"\n{name}: *{count}* раз"

    await update.message.reply_text(text, parse_mode="Markdown")

async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plans = list(WORKOUT_PLANS.keys())
    keyboard = []
    for key in plans:
        p = WORKOUT_PLANS[key]
        keyboard.append([InlineKeyboardButton(p["name"], callback_data=f"plan_{key}")])

    await update.message.reply_text(
        "Выбери план тренировок:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.split("_", 1)[1]

    if plan_key not in WORKOUT_PLANS:
        await query.edit_message_text("❌ План не найден")
        return

    data, uid = get_user_data(query.from_user.id)
    data[uid]["plan"] = plan_key
    save_data(data)

    name = WORKOUT_PLANS[plan_key]["name"]
    await query.edit_message_text(f"✅ Выбран план: *{name}*", parse_mode="Markdown")

# ═══════════════════════════════════════════════
# HEALTH CHECK SERVER (для Railway)
# ═══════════════════════════════════════════════

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Gym Tracker Bot is running!')
    def log_message(self, format, *args):
        pass  # тихий лог

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f'Health server on port {port}')
    server.serve_forever()

# ═══════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════

def main():
    # Запускаем health-check сервер в фоне
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("day1", day1))
    app.add_handler(CommandHandler("day2", day2))
    app.add_handler(CommandHandler("day3", day3))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("weight", weight))
    app.add_handler(CommandHandler("progress", progress))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("plan", plan))

    app.add_handler(CallbackQueryHandler(done_callback, pattern=r"^done_\d+$"))
    app.add_handler(CallbackQueryHandler(plan_callback, pattern=r"^plan_"))

    logger.info("Gym Tracker Bot запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
