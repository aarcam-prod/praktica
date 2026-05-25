
import os
import logging
from datetime import datetime

import telebot
from telebot import types

import db_handler as db
import analyzer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "сюда надо вставить токен, чтобы заработало")
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")


user_states: dict = {}   # {user_id: {"step": str, ...}}

STEPS = ["mood", "work", "sleep", "comment"]



def main_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("➕ Записать день"),
        types.KeyboardButton("📊 Статистика"),
        types.KeyboardButton("📋 История"),
        types.KeyboardButton("⚙️ Настройки"),
    )
    return kb


def cancel_keyboard() -> types.ReplyKeyboardMarkup:

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Отмена"))
    return kb

def mood_inline() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(f"{v} {k}", callback_data=f"mood_{k}")
        for k, v in analyzer.MOOD_EMOJI.items()
    ]
    kb.row(*buttons)
    return kb


def hours_inline(prefix: str, values: list) -> types.InlineKeyboardMarkup:

    kb = types.InlineKeyboardMarkup(row_width=5)
    buttons = [
        types.InlineKeyboardButton(f"{v} ч", callback_data=f"{prefix}_{v}")
        for v in values

    ] + [types.InlineKeyboardButton("Другое ✏️", callback_data=f"{prefix}_other")]
    kb.add(*buttons)
    return kb


def stats_inline() -> types.InlineKeyboardMarkup:

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📅 За неделю",  callback_data="stats_week"),
        types.InlineKeyboardButton("🗓 За месяц",   callback_data="stats_month"),
        types.InlineKeyboardButton("🔍 Инсайты",    callback_data="stats_insights"),
        types.InlineKeyboardButton("📉 График",     callback_data="stats_chart"),
    )
    return kb


def settings_inline(current_time: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=3)
    times = ["08:00", "12:00", "18:00", "20:00", "21:00", "22:00"]
    buttons = [
        types.InlineKeyboardButton(
            f"{'✅' if t == current_time else ''} {t}",
            callback_data=f"reminder_{t}"
        )
        for t in times
    ]
    kb.add(*buttons)

    return kb


def get_state(user_id: int) -> dict:
    return user_states.get(user_id, {})


def set_state(user_id: int, **kwargs):
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id].update(kwargs)


def clear_state(user_id: int):
    user_states.pop(user_id, None)


@bot.message_handler(commands=["start"])
def cmd_start(msg: types.Message):
    db.upsert_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.first_name or "")
    name = msg.from_user.first_name or "друг"
    text = (
        f"👋 Привет, *{name}*!\n\n"
        "Я — *Трекер настроения и продуктивности*.\n\n"
        "Каждый день я помогу тебе записывать:\n"
        "• 😊 Уровень настроения (1–5)\n"
        "• 💼 Часы работы/учёбы\n"
        "• 🛌 Часы сна\n"
        "• 💬 Опциональный комментарий\n\n"
        "На основе этих данных я покажу *тенденции и инсайты* о твоём образе жизни.\n\n"
        "Начни с кнопки *«➕ Записать день»* ниже 👇"
    )

    bot.send_message(msg.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=["help"])

def cmd_help(msg: types.Message):
    text = (
        "📖 *Справка по боту*\n\n"
        "*/start* — Перезапуск и приветствие\n"
        "*/add* — Записать данные за сегодня\n"
        "*/stats* — Статистика и графики\n"
        "*/history* — История последних записей\n"
        "*/settings* — Настройки напоминаний\n"
        "*/clear* — Удаление всех данных\n"
        "*/help* — Эта справка\n\n"
        "Или пользуйся кнопками внизу экрана 😊"
    )
    bot.send_message(msg.chat.id, text, reply_markup=main_keyboard())


@bot.message_handler(commands=["add"])

@bot.message_handler(func=lambda m: m.text == "➕ Записать день")
def cmd_add(msg: types.Message):

    user_id = msg.from_user.id
    db.upsert_user(user_id, msg.from_user.username or "", msg.from_user.first_name or "")

    if db.entry_exists_today(user_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✏️ Перезаписать", callback_data="overwrite_yes"),
            types.InlineKeyboardButton("❌ Отмена",       callback_data="overwrite_no"),
        )
        bot.send_message(
            msg.chat.id,
            "⚠️ Ты уже добавлял запись сегодня. Хочешь перезаписать?",
            reply_markup=kb,
        )
        return

    _start_entry_flow(msg.chat.id, user_id)



def _start_entry_flow(chat_id: int, user_id: int):
    set_state(user_id, step="mood", chat_id=chat_id)
    bot.send_message(
        chat_id,
        "😊 *Шаг 1/4*\nОцени своё настроение сегодня:",
        reply_markup=cancel_keyboard(),
    )
    bot.send_message(chat_id, "1 — ужасно, 5 — отлично 👇", reply_markup=mood_inline())


@bot.message_handler(commands=["stats"])
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def cmd_stats(msg: types.Message):
    bot.send_message(
        msg.chat.id,
        "📊 *Что хочешь узнать?*",
        reply_markup=stats_inline(),
    )


@bot.message_handler(commands=["history"])
@bot.message_handler(func=lambda m: m.text == "📋 История")
def cmd_history(msg: types.Message):
    entries = db.get_all_entries(msg.from_user.id, limit=14)
    text = analyzer.format_history_text(entries)
    bot.send_message(msg.chat.id, text, reply_markup=main_keyboard())


@bot.message_handler(commands=["settings"])
@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def cmd_settings(msg: types.Message):

    user = db.get_user(msg.from_user.id)

    if not user:

        db.upsert_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.first_name or "")
        user = db.get_user(msg.from_user.id)

    current = user.get("reminder_time", "20:00")
    text = (
        f"⚙️ *Настройки*\n\n"
        f"Текущее время напоминания: *{current}*\n\n"
        "Выбери новое время:"
    )
    bot.send_message(msg.chat.id, text, reply_markup=settings_inline(current))


@bot.message_handler(commands=["clear"])
def cmd_clear(msg: types.Message):

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton("🗑 Да, удалить всё", callback_data="clear_yes"),
        types.InlineKeyboardButton("❌ Отмена",           callback_data="clear_no"),
    )
    bot.send_message(
        msg.chat.id,
        "⚠️ *Внимание!* Ты собираешься удалить *все* свои записи.\n\nЭто действие необратимо. Продолжить?",
        reply_markup=kb,
    )



@bot.callback_query_handler(func=lambda c: c.data.startswith("mood_"))

def cb_mood(call: types.CallbackQuery):

    user_id = call.from_user.id

    state = get_state(user_id)
    if state.get("step") != "mood":
        bot.answer_callback_query(call.id, "Начни заново: /add")
        return

    mood = int(call.data.split("_")[1])
    set_state(user_id, mood=mood, step="work")
    bot.answer_callback_query(call.id, f"Настроение: {analyzer.MOOD_EMOJI[mood]} {mood}/5")
    bot.edit_message_text(
        f"✅ Настроение: {analyzer.MOOD_EMOJI[mood]} *{analyzer.MOOD_LABEL[mood]}*",
        call.message.chat.id, call.message.message_id,
    )
    bot.send_message(
        call.message.chat.id,
        "💼 *Шаг 2/4*\nСколько часов ты потратил на работу/учёбу?",
        reply_markup=hours_inline("work", [0.5, 1, 2, 3, 4, 6, 8]),
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("work_"))
def cb_work(call: types.CallbackQuery):

    user_id = call.from_user.id
    state = get_state(user_id)

    if state.get("step") != "work":
        bot.answer_callback_query(call.id)
        return

    value = call.data.split("_")[1]
    
    if value == "other":
        set_state(user_id, step="work_manual")
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✏️ Введи количество часов числом (например: 3.5):")
        return

    hours = float(value)
    set_state(user_id, work_hours=hours, step="sleep")
    bot.answer_callback_query(call.id, f"Работа: {hours} ч")
    bot.edit_message_text(
        f"✅ Работа/учёба: *{hours} ч*",
        call.message.chat.id, call.message.message_id,
    )
    bot.send_message(
        call.message.chat.id,
        "🛌 *Шаг 3/4*\nСколько часов ты спал?",
        reply_markup=hours_inline("sleep", [5, 6, 7, 8, 9, 10]),
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("sleep_"))
def cb_sleep(call: types.CallbackQuery):
    user_id = call.from_user.id
    state = get_state(user_id)
    if state.get("step") != "sleep":
        bot.answer_callback_query(call.id)
        return

    value = call.data.split("_")[1]
    if value == "other":
        set_state(user_id, step="sleep_manual")
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✏️ Введи количество часов сна (например: 7.5):")
        return

    hours = float(value)
    set_state(user_id, sleep_hours=hours, step="comment")
    bot.answer_callback_query(call.id, f"Сон: {hours} ч")
    bot.edit_message_text(
        f"✅ Сон: *{hours} ч*",
        call.message.chat.id, call.message.message_id,
    )
    _ask_comment(call.message.chat.id, user_id)


def _ask_comment(chat_id: int, user_id: int):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⏭ Пропустить", callback_data="comment_skip"))
    bot.send_message(
        chat_id,
        "💬 *Шаг 4/4* _(опционально)_\nДобавь комментарий о дне или нажми «Пропустить»:",
        reply_markup=kb,
    )


@bot.callback_query_handler(func=lambda c: c.data == "comment_skip")
def cb_comment_skip(call: types.CallbackQuery):
    user_id = call.from_user.id
    state = get_state(user_id)
    if state.get("step") != "comment":
        bot.answer_callback_query(call.id)
        return
    bot.answer_callback_query(call.id)
    bot.edit_message_text("⏭ Комментарий пропущен.", call.message.chat.id, call.message.message_id)
    _save_and_confirm(call.message.chat.id, user_id, comment=None)


@bot.callback_query_handler(func=lambda c: c.data.startswith("stats_"))
def cb_stats(call: types.CallbackQuery):
    user_id = call.from_user.id
    action = call.data.split("_")[1]
    bot.answer_callback_query(call.id, "Загружаю…")

    if action == "week":
        entries = db.get_stats(user_id, "week")
        text = analyzer.format_stats_text(entries, "за неделю")
        bot.send_message(call.message.chat.id, text, reply_markup=main_keyboard())

    elif action == "month":
        entries = db.get_stats(user_id, "month")
        text = analyzer.format_stats_text(entries, "за месяц")
        bot.send_message(call.message.chat.id, text, reply_markup=main_keyboard())

    elif action == "insights":
        insights = db.get_insights(user_id)
        text = analyzer.format_insights_text(insights)
        bot.send_message(call.message.chat.id, text, reply_markup=main_keyboard())

    elif action == "chart":
        entries = db.get_stats(user_id, "month")
        if len(entries) < 2:
            bot.send_message(call.message.chat.id,
                             "📭 Нужно хотя бы 2 записи для построения графика.",
                             reply_markup=main_keyboard())
            return
        chart = analyzer.build_chart(entries)
        if chart:
            bot.send_photo(call.message.chat.id, chart, caption="📉 График за последние 30 дней")
        else:
            bot.send_message(call.message.chat.id,
                             "⚠️ Matplotlib не установлен. Установи его: `pip install matplotlib`",
                             reply_markup=main_keyboard())


@bot.callback_query_handler(func=lambda c: c.data.startswith("reminder_"))
def cb_reminder(call: types.CallbackQuery):
    time_str = call.data.replace("reminder_", "")
    db.update_reminder_time(call.from_user.id, time_str)
    bot.answer_callback_query(call.id, f"Напоминание установлено на {time_str}")
    bot.edit_message_text(
        f"⚙️ *Настройки*\n\nВремя напоминания обновлено: *{time_str}* ✅\n\n"
        "_Функция планировщика напоминаний может требовать отдельной настройки сервера._",
        call.message.chat.id, call.message.message_id,
    )


@bot.callback_query_handler(func=lambda c: c.data in ("overwrite_yes", "overwrite_no"))
def cb_overwrite(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    if call.data == "overwrite_yes":
        bot.edit_message_text("✏️ Хорошо, перезапишем!", call.message.chat.id, call.message.message_id)
        _start_entry_flow(call.message.chat.id, call.from_user.id)
    else:
        bot.edit_message_text("❌ Отменено.", call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda c: c.data in ("clear_yes", "clear_no"))
def cb_clear(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    if call.data == "clear_yes":
        db.clear_user_data(call.from_user.id)
        bot.edit_message_text("🗑 Все данные удалены.", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ Удаление отменено.", call.message.chat.id, call.message.message_id)



@bot.message_handler(func=lambda m: True)
def handle_text(msg: types.Message):
    user_id = msg.from_user.id

    # Кнопка отмены
    if msg.text == "❌ Отмена":
        clear_state(user_id)
        bot.send_message(msg.chat.id, "❌ Ввод отменён.", reply_markup=main_keyboard())
        return

    state = get_state(user_id)
    step = state.get("step")

    if step == "work_manual":
        try:
            hours = float(msg.text.replace(",", "."))
            if hours < 0 or hours > 24:
                raise ValueError
            set_state(user_id, work_hours=hours, step="sleep")
            bot.send_message(
                msg.chat.id,
                f"✅ Работа/учёба: *{hours} ч*\n\n🛌 *Шаг 3/4*\nСколько часов ты спал?",
                reply_markup=hours_inline("sleep", [5, 6, 7, 8, 9, 10]),
            )
        except ValueError:
            bot.send_message(msg.chat.id, "⚠️ Введи число от 0 до 24 (например: 3 или 2.5)")

    elif step == "sleep_manual":
        try:
            hours = float(msg.text.replace(",", "."))
            if hours < 0 or hours > 24:
                raise ValueError
            set_state(user_id, sleep_hours=hours, step="comment")
            bot.send_message(msg.chat.id, f"✅ Сон: *{hours} ч*")
            _ask_comment(msg.chat.id, user_id)
        except ValueError:
            bot.send_message(msg.chat.id, "⚠️ Введи число от 0 до 24 (например: 7 или 6.5)")

    elif step == "comment":
        _save_and_confirm(msg.chat.id, user_id, comment=msg.text)

    else:
        bot.send_message(
            msg.chat.id,
            "Используй кнопки меню или команды.\nНапечатай /help для справки.",
            reply_markup=main_keyboard(),
        )


def _save_and_confirm(chat_id: int, user_id: int, comment: str | None):
    state = get_state(user_id)
    try:
        db.save_entry(
            user_id=user_id,
            mood=state["mood"],
            work_hours=state["work_hours"],
            sleep_hours=state["sleep_hours"],
            comment=comment,
        )
        mood_icon = analyzer.MOOD_EMOJI.get(state["mood"], "")
        text = (
            f"✅ *Запись сохранена!*\n\n"
            f"😊 Настроение: {mood_icon} {state['mood']}/5\n"
            f"💼 Работа: {state['work_hours']} ч\n"
            f"🛌 Сон: {state['sleep_hours']} ч\n"
        )
        if comment:
            text += f"💬 Комментарий: _{comment}_\n"
        text += "\n_Отличная работа! Продолжай вести записи для лучших инсайтов._ 🌟"
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")
        text = "❌ Ошибка при сохранении. Попробуй ещё раз."

    clear_state(user_id)
    bot.send_message(chat_id, text, reply_markup=main_keyboard())



if __name__ == "__main__":
    db.init_db()
    logger.info("🤖 Бот запущен. Нажми Ctrl+C для остановки.")
    bot.infinity_polling(logger_level=logging.WARNING)
