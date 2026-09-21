import os
import logging
from datetime import datetime

from telegram import InlineKeyboardButton as B, InlineKeyboardMarkup as M, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])

GIS = "https://go.2gis.com/qE6oV"
SITE = "https://imperialkitchen.kz"
SUPPORT = "https://t.me/imperialkitchen95"

DATA_DIR = "/data"
PERSISTENCE_FILE = os.path.join(DATA_DIR, "imperial_bot_data.pkl")

os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# =========================
# КНОПКИ
# =========================

def home():
    return M([
        [B("🍣 Оценить заказ", callback_data="review")],
        [B("💬 Связаться с поддержкой", url=SUPPORT)],
    ])


def stars():
    return M([
        [
            B("⭐ 1", callback_data="r1"),
            B("⭐ 2", callback_data="r2"),
            B("⭐ 3", callback_data="r3"),
        ],
        [
            B("⭐ 4", callback_data="r4"),
            B("⭐ 5", callback_data="r5"),
        ],
    ])


def reasons():
    return M([
        [B("🍣 Качество блюда", callback_data="x_food")],
        [B("🚗 Доставка", callback_data="x_delivery")],
        [B("📦 Ошибка в заказе", callback_data="x_order")],
        [B("🙋 Обслуживание", callback_data="x_service")],
        [B("💬 Другое", callback_data="x_other")],
    ])


def finish():
    return M([
        [B("💬 Связаться с поддержкой", url=SUPPORT)],
        [B("🔄 Оценить другой заказ", callback_data="review")],
    ])


def admin_new_buttons(user_id):
    return M([
        [B("🟡 Взять в работу", callback_data=f"admin_work:{user_id}")],
        [B("💬 Ответить клиенту", callback_data=f"admin_reply:{user_id}")],
        [B("✅ Закрыть обращение", callback_data=f"admin_close:{user_id}")],
    ])


def admin_work_buttons(user_id):
    return M([
        [B("💬 Ответить клиенту", callback_data=f"admin_reply:{user_id}")],
        [B("✅ Закрыть обращение", callback_data=f"admin_close:{user_id}")],
    ])


def admin_closed_buttons(user_id):
    return M([
        [B("💬 Ответить клиенту", callback_data=f"admin_reply:{user_id}")],
    ])


# =========================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# =========================

def is_admin(u):
    return u.effective_chat and u.effective_chat.id == ADMIN_CHAT_ID


def next_ticket_number(c):
    number = int(c.bot_data.get("ticket_counter", 0)) + 1
    c.bot_data["ticket_counter"] = number
    return f"IK-{number:04d}"


def customer_complaint_count(c, user_id):
    history = c.bot_data.get("customer_history", {})
    return len(history.get(str(user_id), []))


def save_rating(c, user_id, rating):
    ratings = c.bot_data.setdefault("ratings", [])

    ratings.append({
        "user_id": user_id,
        "rating": rating,
        "date": datetime.now().isoformat(),
    })


def save_complaint_history(c, user_id, data):
    history = c.bot_data.setdefault("customer_history", {})
    history.setdefault(str(user_id), []).append(data)


# =========================
# СТАРТ
# =========================

async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data.clear()

    await u.message.reply_text(
        "🍣 Imperial Kitchen\n\n"
        "Спасибо, что выбрали нас ❤️\n\n"
        "Нам важно, чтобы каждый заказ радовал вас. "
        "Оцените свой заказ — это займёт меньше минуты.",
        reply_markup=home(),
    )


# =========================
# ОЦЕНКА
# =========================

async def review(u, c):
    c.user_data.clear()

    q = u.callback_query
    await q.answer()

    await q.edit_message_text(
        "Как вам заказ Imperial Kitchen?\n\n"
        "Поставьте, пожалуйста, оценку:",
        reply_markup=stars(),
    )


async def rating(u, c):
    q = u.callback_query
    await q.answer()

    v = int(q.data[1:])
    c.user_data["rating"] = v

    save_rating(c, u.effective_user.id, v)

    if v >= 4:
        c.user_data.clear()

        await q.edit_message_text(
            "❤️ Спасибо за высокую оценку!\n\n"
            "Нам будет очень приятно, если вы поделитесь "
            "своим впечатлением об Imperial Kitchen:",
            reply_markup=M([
                [B("⭐ Оставить отзыв в 2GIS", url=GIS)],
                [B("🌐 Оставить отзыв на сайте", url=SITE)],
                [B("🔄 Оценить другой заказ", callback_data="review")],
            ]),
        )
        return

    c.user_data["stage"] = "order"

    await q.edit_message_text(
        "😔 Спасибо, что сообщили нам.\n\n"
        "Мы хотим разобраться в ситуации.\n\n"
        "Напишите, пожалуйста, номер вашего заказа.",
        reply_markup=M([
            [B("Не знаю номер заказа", callback_data="unknown")]
        ]),
    )


# =========================
# ЖАЛОБА
# =========================

async def unknown(u, c):
    q = u.callback_query
    await q.answer()

    c.user_data["order"] = "не указан"
    c.user_data["stage"] = "reason"

    await q.edit_message_text(
        "Что именно пошло не так?",
        reply_markup=reasons(),
    )


async def reason(u, c):
    q = u.callback_query
    await q.answer()

    d = {
        "x_food": "Качество блюда",
        "x_delivery": "Доставка",
        "x_order": "Ошибка в заказе",
        "x_service": "Обслуживание",
        "x_other": "Другое",
    }

    c.user_data["reason"] = d[q.data]
    c.user_data["stage"] = "comment"

    await q.edit_message_text(
        "Расскажите, пожалуйста, подробнее, что произошло.\n\n"
        "Напишите сообщение ниже. После этого можно будет "
        "приложить фотографию."
    )


# =========================
# ТЕКСТОВЫЕ СООБЩЕНИЯ
# =========================

async def textmsg(u, c):

    # Ответ администратора клиенту
    if is_admin(u):
        admin_state = c.chat_data.get("admin_reply_to")

        if admin_state:
            user_id = admin_state["user_id"]
            text = u.message.text.strip()

            try:
                await c.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "💬 Ответ Imperial Kitchen\n\n"
                        f"{text}\n\n"
                        "Если вам нужно дополнить обращение, "
                        "вы можете написать нашей службе поддержки."
                    ),
                )

                await u.message.reply_text(
                    "✅ Ответ отправлен клиенту."
                )

            except Exception:
                logging.exception("Ошибка отправки ответа клиенту")

                await u.message.reply_text(
                    "❌ Не удалось отправить сообщение клиенту."
                )

            c.chat_data.pop("admin_reply_to", None)
            return

    s = c.user_data.get("stage")

    if s == "order":
        c.user_data["order"] = u.message.text.strip()
        c.user_data["stage"] = "reason"

        await u.message.reply_text(
            "Спасибо. Что именно пошло не так?",
            reply_markup=reasons(),
        )

    elif s == "comment":
        c.user_data["comment"] = u.message.text.strip()
        c.user_data["stage"] = "photo"

        await u.message.reply_text(
            "Если у вас есть фотография проблемы, отправьте её сюда.\n\n"
            "Если фотографии нет — нажмите кнопку ниже.",
            reply_markup=M([
                [B("➡️ Отправить без фото", callback_data="nophoto")]
            ]),
        )


# =========================
# СОЗДАНИЕ ОБРАЩЕНИЯ
# =========================

def admintext(u, c, ticket, previous):
    x = u.effective_user
    un = f"@{x.username}" if x.username else "не указан"

    if previous == 0:
        history_text = "Первое обращение"
    else:
        history_text = f"Ранее обращался: {previous} раз"

    return (
        "🚨 ОБРАЩЕНИЕ — IMPERIAL KITCHEN\n\n"
        f"🎫 № обращения: {ticket}\n"
        "📌 Статус: 🔴 НОВОЕ\n\n"
        f"⭐ Оценка: {c.user_data.get('rating', '?')}/5\n"
        f"🧾 Заказ: {c.user_data.get('order', 'не указан')}\n"
        f"⚠️ Причина: {c.user_data.get('reason', 'не указана')}\n\n"
        f"👤 Клиент: {x.full_name or 'не указано'}\n"
        f"📱 Telegram: {un}\n"
        f"🆔 User ID: {x.id}\n"
        f"📚 История: {history_text}\n\n"
        "💬 Комментарий:\n"
        f"{c.user_data.get('comment', 'нет')}"
    )


async def done(u, c, photo=None):
    user_id = u.effective_user.id

    previous = customer_complaint_count(c, user_id)
    ticket = next_ticket_number(c)

    complaint_data = {
        "ticket": ticket,
        "user_id": user_id,
        "rating": c.user_data.get("rating"),
        "order": c.user_data.get("order", "не указан"),
        "reason": c.user_data.get("reason", "не указана"),
        "comment": c.user_data.get("comment", "нет"),
        "status": "new",
        "date": datetime.now().isoformat(),
    }

    admin_message = await c.bot.send_message(
        ADMIN_CHAT_ID,
        admintext(u, c, ticket, previous),
        reply_markup=admin_new_buttons(user_id),
    )

    complaint_data["admin_message_id"] = admin_message.message_id

    complaints = c.bot_data.setdefault("complaints", {})
    complaints[str(admin_message.message_id)] = complaint_data

    save_complaint_history(
        c,
        user_id,
        complaint_data.copy(),
    )

    if photo:
        await c.bot.send_photo(
            ADMIN_CHAT_ID,
            photo=photo,
            caption=f"📸 Фото к обращению {ticket}",
        )

    c.user_data.clear()

    t = (
        "🙏 Спасибо, что рассказали нам о ситуации.\n\n"
        f"Номер вашего обращения: {ticket}\n\n"
        "Ваше обращение передано руководству Imperial Kitchen. "
        "Мы обязательно разберёмся.\n\n"
        "Если вопрос срочный, вы можете сразу написать "
        "нашей службе поддержки."
    )

    if u.callback_query:
        await u.callback_query.edit_message_text(
            t,
            reply_markup=finish(),
        )
    else:
        await u.message.reply_text(
            t,
            reply_markup=finish(),
        )


async def nophoto(u, c):
    q = u.callback_query
    await q.answer()

    if c.user_data.get("stage") == "photo":
        await done(u, c)


async def photo(u, c):
    if c.user_data.get("stage") == "photo":
        await done(
            u,
            c,
            u.message.photo[-1].file_id,
        )


# =========================
# ОБНОВЛЕНИЕ СТАТУСА В ИСТОРИИ
# =========================

def update_history_status(c, user_id, ticket, status):
    history = c.bot_data.setdefault("customer_history", {})
    items = history.get(str(user_id), [])

    for item in reversed(items):
        if item.get("ticket") == ticket:
            item["status"] = status
            break


# =========================
# АДМИН — В РАБОТУ
# =========================

async def admin_work(u, c):
    q = u.callback_query

    if not is_admin(u):
        await q.answer("Нет доступа.", show_alert=True)
        return

    await q.answer()

    user_id = int(q.data.split(":")[1])
    message_id = str(q.message.message_id)

    complaints = c.bot_data.setdefault("complaints", {})
    complaint = complaints.get(message_id, {})

    ticket = complaint.get("ticket", "неизвестно")

    text = q.message.text.replace(
        "📌 Статус: 🔴 НОВОЕ",
        "📌 Статус: 🟡 В РАБОТЕ",
    )

    await q.edit_message_text(
        text,
        reply_markup=admin_work_buttons(user_id),
    )

    complaint["status"] = "work"
    update_history_status(c, user_id, ticket, "work")


# =========================
# АДМИН — ЗАКРЫТЬ
# =========================

async def admin_close(u, c):
    q = u.callback_query

    if not is_admin(u):
        await q.answer("Нет доступа.", show_alert=True)
        return

    await q.answer()

    user_id = int(q.data.split(":")[1])
    message_id = str(q.message.message_id)

    complaints = c.bot_data.setdefault("complaints", {})
    complaint = complaints.get(message_id, {})

    ticket = complaint.get("ticket", "неизвестно")

    text = q.message.text

    text = text.replace(
        "📌 Статус: 🔴 НОВОЕ",
        "📌 Статус: ✅ РЕШЕНО",
    )

    text = text.replace(
        "📌 Статус: 🟡 В РАБОТЕ",
        "📌 Статус: ✅ РЕШЕНО",
    )

    await q.edit_message_text(
        text,
        reply_markup=admin_closed_buttons(user_id),
    )

    complaint["status"] = "closed"
    update_history_status(c, user_id, ticket, "closed")

    try:
        await c.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Обращение {ticket} отмечено как решённое.\n\n"
                "Спасибо, что помогаете Imperial Kitchen "
                "становиться лучше ❤️"
            ),
        )
    except Exception:
        logging.exception("Ошибка уведомления клиента")


# =========================
# АДМИН — ОТВЕТИТЬ
# =========================

async def admin_reply(u, c):
    q = u.callback_query

    if not is_admin(u):
        await q.answer("Нет доступа.", show_alert=True)
        return

    await q.answer()

    user_id = int(q.data.split(":")[1])

    c.chat_data["admin_reply_to"] = {
        "user_id": user_id,
        "admin_message_id": q.message.message_id,
    }

    await q.message.reply_text(
        "✍️ Напишите ответ клиенту следующим сообщением.\n\n"
        "Я отправлю его клиенту от имени Imperial Kitchen.\n\n"
        "Для отмены нажмите /cancelreply"
    )


async def cancelreply(u, c):
    if not is_admin(u):
        return

    if c.chat_data.get("admin_reply_to"):
        c.chat_data.pop("admin_reply_to", None)

        await u.message.reply_text(
            "❌ Отправка ответа отменена."
        )
    else:
        await u.message.reply_text(
            "Сейчас нет активного ответа клиенту."
        )


# =========================
# СТАТИСТИКА
# =========================

async def stats(u, c):
    if not is_admin(u):
        return

    ratings = c.bot_data.get("ratings", [])
    complaints = c.bot_data.get("complaints", {})

    total_ratings = len(ratings)

    if total_ratings:
        average = sum(
            int(x.get("rating", 0))
            for x in ratings
        ) / total_ratings
    else:
        average = 0

    stars_count = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
    }

    for item in ratings:
        value = int(item.get("rating", 0))

        if value in stars_count:
            stars_count[value] += 1

    new_count = 0
    work_count = 0
    closed_count = 0

    reasons_count = {}

    for item in complaints.values():
        status = item.get("status")

        if status == "new":
            new_count += 1
        elif status == "work":
            work_count += 1
        elif status == "closed":
            closed_count += 1

        reason_name = item.get("reason")

        if reason_name:
            reasons_count[reason_name] = (
                reasons_count.get(reason_name, 0) + 1
            )

    if reasons_count:
        reasons_sorted = sorted(
            reasons_count.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        reasons_text = "\n".join(
            f"• {name}: {count}"
            for name, count in reasons_sorted
        )
    else:
        reasons_text = "Пока нет данных"

    text = (
        "📊 СТАТИСТИКА — IMPERIAL KITCHEN\n\n"
        f"⭐ Всего оценок: {total_ratings}\n"
        f"📈 Средняя оценка: {average:.2f}/5\n\n"

        "Распределение оценок:\n"
        f"⭐ 5 — {stars_count[5]}\n"
        f"⭐ 4 — {stars_count[4]}\n"
        f"⭐ 3 — {stars_count[3]}\n"
        f"⭐ 2 — {stars_count[2]}\n"
        f"⭐ 1 — {stars_count[1]}\n\n"

        "🚨 ОБРАЩЕНИЯ\n\n"
        f"🔴 Новые: {new_count}\n"
        f"🟡 В работе: {work_count}\n"
        f"✅ Решено: {closed_count}\n"
        f"📦 Всего обращений: {len(complaints)}\n\n"

        "⚠️ Причины обращений:\n"
        f"{reasons_text}"
    )

    await u.message.reply_text(text)


# =========================
# ИСТОРИЯ КЛИЕНТА
# =========================

async def history(u, c):
    if not is_admin(u):
        return

    if not c.chat_data.get("history_user_id"):
        await u.message.reply_text(
            "Чтобы посмотреть историю клиента, отправьте:\n\n"
            "/history USER_ID\n\n"
            "Например:\n"
            "/history 5284790085"
        )
        return


async def history_command(u, c):
    if not is_admin(u):
        return

    if not c.args:
        await u.message.reply_text(
            "Использование:\n/history USER_ID"
        )
        return

    user_id = c.args[0]

    customer_history = c.bot_data.get(
        "customer_history",
        {}
    ).get(str(user_id), [])

    if not customer_history:
        await u.message.reply_text(
            "По этому клиенту обращений пока нет."
        )
        return

    lines = [
        "📚 ИСТОРИЯ КЛИЕНТА",
        f"🆔 User ID: {user_id}",
        f"📦 Всего обращений: {len(customer_history)}",
        "",
    ]

    for item in reversed(customer_history[-10:]):
        status = item.get("status", "new")

        status_text = {
            "new": "🔴 Новое",
            "work": "🟡 В работе",
            "closed": "✅ Решено",
        }.get(status, status)

        lines.extend([
            f"🎫 {item.get('ticket', '?')}",
            f"⭐ {item.get('rating', '?')}/5",
            f"🧾 Заказ: {item.get('order', 'не указан')}",
            f"⚠️ {item.get('reason', 'не указана')}",
            f"📌 {status_text}",
            "",
        ])

    await u.message.reply_text(
        "\n".join(lines)
    )


# =========================
# ОТМЕНА
# =========================

async def cancel(u, c):
    c.user_data.clear()

    await u.message.reply_text(
        "Опрос отменён. Можно начать заново.",
        reply_markup=home(),
    )


# =========================
# ЗАПУСК
# =========================

def main():
    persistence = PicklePersistence(
        filepath=PERSISTENCE_FILE
    )

    a = (
        Application.builder()
        .token(TOKEN)
        .persistence(persistence)
        .build()
    )

    a.add_handler(CommandHandler("start", start))
    a.add_handler(CommandHandler("cancel", cancel))
    a.add_handler(CommandHandler("cancelreply", cancelreply))
    a.add_handler(CommandHandler("stats", stats))
    a.add_handler(CommandHandler("history", history_command))

    a.add_handler(
        CallbackQueryHandler(
            admin_work,
            pattern=r"^admin_work:\d+$",
        )
    )

    a.add_handler(
        CallbackQueryHandler(
            admin_reply,
            pattern=r"^admin_reply:\d+$",
        )
    )

    a.add_handler(
        CallbackQueryHandler(
            admin_close,
            pattern=r"^admin_close:\d+$",
        )
    )

    a.add_handler(
        CallbackQueryHandler(
            review,
            pattern="^review$",
        )
    )

    a.add_handler(
        CallbackQueryHandler(
            rating,
            pattern="^r[1-5]$",
        )
    )

    a.add_handler(
        CallbackQueryHandler(
            unknown,
            pattern="^unknown$",
        )
    )

    a.add_handler(
        CallbackQueryHandler(
            reason,
            pattern="^x_",
        )
    )

    a.add_handler(
        CallbackQueryHandler(
            nophoto,
            pattern="^nophoto$",
        )
    )

    a.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo,
        )
    )

    a.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            textmsg,
        )
    )

    a.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
