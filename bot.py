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
        "rotation": [1, 3, 2, 3],
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
            "next_day": 1,
            "rotation_idx": 0
        }
        save_data(data)
    return data, uid

# ═══════════════════════════════════════════════
# КОМАНДЫ БОТА
# ═══════════════════════════════════════════════

async def start(update, context):
    user = update.effective_user
    text = (
        f"🏋️ *Gym Tracker Bot*\n"
        f"Привет, {user.first_name}!\n\n"
        f"Команды:\n"
        f"/today — 🏋️ Начать тренировку\n"
        f"/done — ✅ Завершить тренировку\n"
        f"/weight 84 — ⚖️ Записать вес\n"
        f"/progress — 📊 История веса\n"
        f"/history — 📋 Журнал тренировок\n"
        f"/plan — 🔄 Выбрать план\n"
        f"/lastworkout — 📝 Последняя тренировка\n"
        f"/reset — 🗑 Сбросить данные"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

def get_plan(data, uid):
    plan_key = data[uid].get("plan", "dima")
    if plan_key not in WORKOUT_PLANS:
        plan_key = "dima"
    return plan_key, WORKOUT_PLANS[plan_key]

# ═══════════════════════════════════════════════
# ТРЕНИРОВКА С ЗАПИСЬЮ УПРАЖНЕНИЙ
# ═══════════════════════════════════════════════

def build_workout_message(plan, day_num, logged_exercises):
    """Собирает сообщение тренировки с отметками выполненных упражнений"""
    day = plan["days"][day_num]
    lines = [f"*{day['title']}*\n"]

    for i, ex in enumerate(day["exercises"], 1):
        log = logged_exercises.get(str(i))
        if log:
            lines.append(f"✅ {i}. {ex['name']} — *{log}*")
        else:
            lines.append(f"⬜ {i}. {ex['name']} — _{ex['sets']}_")

    done_count = len(logged_exercises)
    total = len(day["exercises"])
    lines.append(f"\n📊 Выполнено: *{done_count}/{total}*")

    if day.get("cardio"):
        lines.append(f"\n{day['cardio']}")

    return "\n".join(lines)

def build_exercise_keyboard(plan, day_num, logged_exercises):
    """Кнопки для каждого упражнения + кнопка завершения"""
    day = plan["days"][day_num]
    keyboard = []

    for i, ex in enumerate(day["exercises"], 1):
        if str(i) not in logged_exercises:
            # Сокращённое название для кнопки
            short_name = ex["name"][:30]
            keyboard.append([InlineKeyboardButton(
                f"📝 {i}. {short_name}",
                callback_data=f"ex_{day_num}_{i}"
            )])

    keyboard.append([InlineKeyboardButton(
        "✅ Завершить тренировку",
        callback_data=f"finish_{day_num}"
    )])

    return InlineKeyboardMarkup(keyboard)

async def today(update, context):
    """Показывает выбор дня тренировки"""
    data, uid = get_user_data(update.effective_user.id)
    plan_key, plan = get_plan(data, uid)
    next_day = data[uid].get("next_day", 1)

    keyboard = []
    for day_num in sorted(plan["days"].keys()):
        day_data = plan["days"][day_num]
        title = day_data["title"]
        if day_num == next_day:
            title = f"⭐ {title}"
        keyboard.append([InlineKeyboardButton(title, callback_data=f"startday_{day_num}")])

    await update.message.reply_text(
        "🏋️ *Выбери тренировку:*\n_(⭐ = следующая по плану)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def startday_callback(update, context):
    """Начинает тренировку выбранного дня"""
    query = update.callback_query
    await query.answer()
    day_num = int(query.data.split("_")[1])

    data, uid = get_user_data(query.from_user.id)
    plan_key, plan = get_plan(data, uid)

    # Создаём сессию тренировки
    data[uid]["current_workout"] = {
        "day": day_num,
        "exercises": {},
        "started": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    save_data(data)

    logged = data[uid]["current_workout"]["exercises"]
    text = build_workout_message(plan, day_num, logged)
    keyboard = build_exercise_keyboard(plan, day_num, logged)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def exercise_callback(update, context):
    """Когда пользователь нажимает на упражнение"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    day_num = int(parts[1])
    ex_idx = int(parts[2])

    data, uid = get_user_data(query.from_user.id)
    plan_key, plan = get_plan(data, uid)
    exercise = plan["days"][day_num]["exercises"][ex_idx - 1]

    # Сохраняем контекст: какое упражнение записываем
    data[uid]["pending_exercise"] = {
        "day": day_num,
        "index": ex_idx,
        "name": exercise["name"]
    }
    save_data(data)

    await query.message.reply_text(
        f"📝 *{exercise['name']}*\n"
        f"План: _{exercise['sets']}_\n\n"
        f"Напиши результат, например:\n"
        f"`40 12` — 40 кг, 12 повторений\n"
        f"`3x12 40кг` — любой формат\n"
        f"или просто текст: `без веса`",
        parse_mode="Markdown"
    )

async def handle_exercise_input(update, context):
    """Обрабатывает ввод веса/повторений"""
    data, uid = get_user_data(update.effective_user.id)

    pending = data[uid].get("pending_exercise")
    if not pending:
        return  # Нет ожидающего упражнения — игнорируем

    text_input = update.message.text.strip()
    day_num = pending["day"]
    ex_idx = pending["index"]
    ex_name = pending["name"]

    # Сохраняем результат в текущую тренировку
    if "current_workout" not in data[uid]:
        data[uid]["current_workout"] = {"day": day_num, "exercises": {}, "started": datetime.now().strftime("%Y-%m-%d %H:%M")}

    data[uid]["current_workout"]["exercises"][str(ex_idx)] = text_input

    # Убираем pending
    del data[uid]["pending_exercise"]
    save_data(data)

    plan_key, plan = get_plan(data, uid)
    logged = data[uid]["current_workout"]["exercises"]

    # Обновляем сообщение с тренировкой
    msg_text = build_workout_message(plan, day_num, logged)
    keyboard = build_exercise_keyboard(plan, day_num, logged)

    await update.message.reply_text(
        f"✅ *{ex_name}*: {text_input}\n",
        parse_mode="Markdown"
    )
    await update.message.reply_text(msg_text, parse_mode="Markdown", reply_markup=keyboard)

async def finish_workout_callback(update, context):
    """Завершает тренировку и сохраняет в лог"""
    query = update.callback_query
    await query.answer()

    day_num = int(query.data.split("_")[1])
    data, uid = get_user_data(query.from_user.id)
    plan_key, plan = get_plan(data, uid)

    workout = data[uid].get("current_workout", {})
    logged = workout.get("exercises", {})

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    day_title = plan["days"][day_num]["title"]

    # Сохраняем полный лог тренировки
    workout_entry = {
        "day": day_num,
        "name": day_title,
        "date": now,
        "exercises": {}
    }

    # Записываем каждое упражнение с результатом
    for i, ex in enumerate(plan["days"][day_num]["exercises"], 1):
        result = logged.get(str(i), "—")
        workout_entry["exercises"][ex["name"]] = result

    data[uid]["workout_log"].append(workout_entry)

    # Следующий день по ротации
    rotation = plan.get("rotation", list(plan["days"].keys()))
    current_idx = data[uid].get("rotation_idx", 0)
    next_idx = (current_idx + 1) % len(rotation)
    data[uid]["rotation_idx"] = next_idx
    data[uid]["next_day"] = rotation[next_idx]

    # Очищаем текущую тренировку
    data[uid]["current_workout"] = {}
    if "pending_exercise" in data[uid]:
        del data[uid]["pending_exercise"]
    save_data(data)

    total = len(data[uid]["workout_log"])
    next_title = plan["days"][data[uid]["next_day"]]["title"]

    # Формируем итог
    text = f"🎉 *Тренировка завершена!*\n\n"
    text += f"📅 {day_title}\n"
    text += f"🕐 {now}\n\n"

    for i, ex in enumerate(plan["days"][day_num]["exercises"], 1):
        result = logged.get(str(i), "—")
        text += f"{'✅' if str(i) in logged else '⬜'} {ex['name']}: *{result}*\n"

    text += f"\n📊 Всего тренировок: *{total}*\n"
    text += f"➡️ Следующая: {next_title}"

    await query.edit_message_text(text, parse_mode="Markdown")

# ═══════════════════════════════════════════════
# ПОСЛЕДНЯЯ ТРЕНИРОВКА
# ═══════════════════════════════════════════════

async def lastworkout(update, context):
    """Показывает подробности последней тренировки"""
    data, uid = get_user_data(update.effective_user.id)
    logs = data[uid].get("workout_log", [])

    if not logs:
        await update.message.reply_text("Пока нет тренировок. Жми /today! 💪")
        return

    last = logs[-1]
    text = f"📝 *Последняя тренировка*\n\n"
    text += f"📅 {last['name']}\n"
    text += f"🕐 {last['date']}\n\n"

    exercises = last.get("exercises", {})
    if exercises:
        for name, result in exercises.items():
            text += f"• {name}: *{result}*\n"
    else:
        text += "_Без детальной записи_"

    await update.message.reply_text(text, parse_mode="Markdown")

# ═══════════════════════════════════════════════
# ВЕС И ПРОГРЕСС
# ═══════════════════════════════════════════════

async def weight(update, context):
    if not context.args:
        await update.message.reply_text("Укажи вес: `/weight 84.5`", parse_mode="Markdown")
        return
    try:
        w = float(context.args[0].replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Введи число: `/weight 84.5`", parse_mode="Markdown")
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

async def progress(update, context):
    data, uid = get_user_data(update.effective_user.id)
    logs = data[uid].get("weight_log", [])
    if not logs:
        await update.message.reply_text("Пока нет записей. `/weight 85`", parse_mode="Markdown")
        return

    text = "📊 *История веса:*\n\n"
    for entry in logs[-15:]:
        text += f"📅 {entry['date']} — *{entry['weight']} кг*\n"

    first = logs[0]["weight"]
    last = logs[-1]["weight"]
    diff = last - first
    emoji = "📉" if diff < 0 else "📈" if diff > 0 else "➡️"
    text += f"\n{emoji} Итого: *{diff:+.1f} кг*"

    await update.message.reply_text(text, parse_mode="Markdown")

async def history(update, context):
    data, uid = get_user_data(update.effective_user.id)
    logs = data[uid].get("workout_log", [])
    if not logs:
        await update.message.reply_text("Пока нет тренировок. Жми /today! 💪")
        return

    text = "📋 *Журнал тренировок:*\n\n"
    for entry in logs[-10:]:
        ex_count = len(entry.get("exercises", {}))
        ex_info = f" ({ex_count} упр.)" if ex_count else ""
        text += f"📅 {entry['date']} — *{entry['name']}*{ex_info}\n"

    text += f"\n📊 Всего: *{len(logs)}* тренировок"
    await update.message.reply_text(text, parse_mode="Markdown")

async def plan(update, context):
    keyboard = []
    for key, p in WORKOUT_PLANS.items():
        keyboard.append([InlineKeyboardButton(p["name"], callback_data=f"plan_{key}")])
    await update.message.reply_text(
        "Выбери план тренировок:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def plan_callback(update, context):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.split("_", 1)[1]
    if plan_key not in WORKOUT_PLANS:
        await query.edit_message_text("❌ План не найден")
        return
    data, uid = get_user_data(query.from_user.id)
    data[uid]["plan"] = plan_key
    data[uid]["rotation_idx"] = 0
    data[uid]["next_day"] = WORKOUT_PLANS[plan_key]["rotation"][0]
    save_data(data)
    name = WORKOUT_PLANS[plan_key]["name"]
    await query.edit_message_text(f"✅ Выбран план: *{name}*", parse_mode="Markdown")

async def done_command(update, context):
    """Быстрое завершение тренировки без записи упражнений"""
    data, uid = get_user_data(update.effective_user.id)
    plan_key, plan = get_plan(data, uid)
    keyboard = []
    for day_num in sorted(plan["days"].keys()):
        day_data = plan["days"][day_num]
        keyboard.append([InlineKeyboardButton(day_data["title"], callback_data=f"quickdone_{day_num}")])
    await update.message.reply_text(
        "Какую тренировку завершил(а)?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def quickdone_callback(update, context):
    """Быстрая запись тренировки без деталей"""
    query = update.callback_query
    await query.answer()
    day = int(query.data.split("_")[1])
    data, uid = get_user_data(query.from_user.id)
    plan_key, plan = get_plan(data, uid)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    day_title = plan["days"][day]["title"]

    data[uid]["workout_log"].append({
        "day": day, "name": day_title, "date": now, "exercises": {}
    })

    rotation = plan.get("rotation", list(plan["days"].keys()))
    current_idx = data[uid].get("rotation_idx", 0)
    next_idx = (current_idx + 1) % len(rotation)
    data[uid]["rotation_idx"] = next_idx
    data[uid]["next_day"] = rotation[next_idx]
    save_data(data)

    total = len(data[uid]["workout_log"])
    next_title = plan["days"][data[uid]["next_day"]]["title"]

    await query.edit_message_text(
        f"✅ *Тренировка записана!*\n\n"
        f"📅 {day_title}\n🕐 {now}\n"
        f"📊 Всего: *{total}*\n\n"
        f"➡️ Следующая: {next_title}",
        parse_mode="Markdown"
    )

async def reset(update, context):
    """Сброс всех данных пользователя"""
    keyboard = [
        [InlineKeyboardButton("🗑 Да, сбросить всё", callback_data="confirm_reset")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_reset")],
    ]
    await update.message.reply_text(
        "⚠️ *Сбросить все данные?*\n\nБудут удалены:\n• Журнал тренировок\n• История веса\n• Текущая ротация",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def reset_callback(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel_reset":
        await query.edit_message_text("👍 Отменено, данные на месте!")
        return
    data, uid = get_user_data(query.from_user.id)
    plan_key = data[uid].get("plan", "dima")
    data[uid] = {
        "plan": plan_key,
        "weight_log": [],
        "workout_log": [],
        "next_day": 1,
        "rotation_idx": 0
    }
    save_data(data)
    await query.edit_message_text("✅ *Все данные сброшены!*\nМожно начинать заново 💪", parse_mode="Markdown")

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
        pass

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f'Health server on port {port}')
    server.serve_forever()

# ═══════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════

def main():
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("weight", weight))
    app.add_handler(CommandHandler("progress", progress))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("lastworkout", lastworkout))
    app.add_handler(CommandHandler("reset", reset))

    app.add_handler(CallbackQueryHandler(startday_callback, pattern=r"^startday_\d+$"))
    app.add_handler(CallbackQueryHandler(exercise_callback, pattern=r"^ex_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(finish_workout_callback, pattern=r"^finish_\d+$"))
    app.add_handler(CallbackQueryHandler(quickdone_callback, pattern=r"^quickdone_\d+$"))
    app.add_handler(CallbackQueryHandler(plan_callback, pattern=r"^plan_"))
    app.add_handler(CallbackQueryHandler(reset_callback, pattern=r"^(confirm|cancel)_reset$"))

    # Обработка текстовых сообщений (ввод веса/повторений)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_exercise_input))

    logger.info("Gym Tracker Bot запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
