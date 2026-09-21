import os
import logging

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
# КНОПКИ КЛИЕНТА
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


# =========================
# КНОПКИ АДМИНА
# =========================

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


async def textmsg(u, c):

    # ---------------------------------
    # ЕСЛИ ПИШЕТ АДМИН
    # ---------------------------------

    if u.effective_chat.id == ADMIN_CHAT_ID:
        admin_state = c.chat_data.get("admin_reply_to")

        if admin_state:
            user_id = admin_state["user_id"]
            admin_message_id = admin_state.get("admin_message_id")

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

                # Помечаем в карточке, что клиенту ответили
                if admin_message_id:
                    try:
                        old_message = await c.bot.forward_message(
                            chat_id=ADMIN_CHAT_ID,
                            from_chat_id=ADMIN_CHAT_ID,
                            message_id=admin_message_id,
                        )
                        await old_message.delete()
                    except Exception:
                        pass

            except Exception as e:
                logging.exception(e)

                await u.message.reply_text(
                    "❌ Не удалось отправить сообщение клиенту."
                )

            c.chat_data.pop("admin_reply_to", None)
            return

    # ---------------------------------
    # ЕСЛИ ПИШЕТ КЛИЕНТ
    # ---------------------------------

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
# ТЕКСТ ДЛЯ АДМИНА
# =========================

def admintext(u, c, status="🔴 НОВОЕ"):
    x = u.effective_user
    un = f"@{x.username}" if x.username else "не указан"

    return (
        "🚨 ОБРАЩЕНИЕ — IMPERIAL KITCHEN\n\n"
        f"📌 Статус: {status}\n\n"
        f"⭐ Оценка: {c.user_data.get('rating', '?')}/5\n"
        f"🧾 Заказ: {c.user_data.get('order', 'не указан')}\n"
        f"⚠️ Причина: {c.user_data.get('reason', 'не указана')}\n\n"
        f"👤 Клиент: {x.full_name or 'не указано'}\n"
        f"📱 Telegram: {un}\n"
        f"🆔 User ID: {x.id}\n\n"
        "💬 Комментарий:\n"
        f"{c.user_data.get('comment', 'нет')}"
    )


# =========================
# ОТПРАВКА ОБРАЩЕНИЯ
# =========================

async def done(u, c, photo=None):

    user_id = u.effective_user.id

    admin_message = await c.bot.send_message(
        ADMIN_CHAT_ID,
        admintext(u, c),
        reply_markup=admin_new_buttons(user_id),
    )

    # Сохраняем данные карточки
    complaints = c.bot_data.setdefault("complaints", {})

    complaints[str(admin_message.message_id)] = {
        "user_id": user_id,
        "status": "new",
    }

    if photo:
        await c.bot.send_photo(
            ADMIN_CHAT_ID,
            photo=photo,
            caption="📸 Фото к обращению",
        )

    c.user_data.clear()

    t = (
        "🙏 Спасибо, что рассказали нам о ситуации.\n\n"
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
# АДМИН — ВЗЯТЬ В РАБОТУ
# =========================

async def admin_work(u, c):
    q = u.callback_query

    if q.message.chat.id != ADMIN_CHAT_ID:
        await q.answer("Нет доступа.", show_alert=True)
        return

    await q.answer()

    user_id = int(q.data.split(":")[1])

    text = q.message.text

    text = text.replace(
        "📌 Статус: 🔴 НОВОЕ",
        "📌 Статус: 🟡 В РАБОТЕ",
    )

    await q.edit_message_text(
        text,
        reply_markup=admin_work_buttons(user_id),
    )

    complaints = c.bot_data.setdefault("complaints", {})

    if str(q.message.message_id) in complaints:
        complaints[str(q.message.message_id)]["status"] = "work"


# =========================
# АДМИН — ЗАКРЫТЬ
# =========================

async def admin_close(u, c):
    q = u.callback_query

    if q.message.chat.id != ADMIN_CHAT_ID:
        await q.answer("Нет доступа.", show_alert=True)
        return

    await q.answer()

    user_id = int(q.data.split(":")[1])

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

    complaints = c.bot_data.setdefault("complaints", {})

    if str(q.message.message_id) in complaints:
        complaints[str(q.message.message_id)]["status"] = "closed"

    try:
        await c.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ Ваше обращение в Imperial Kitchen отмечено "
                "как решённое.\n\n"
                "Спасибо, что помогаете нам становиться лучше ❤️"
            ),
        )
    except Exception as e:
        logging.exception(e)


# =========================
# АДМИН — ОТВЕТИТЬ
# =========================

async def admin_reply(u, c):
    q = u.callback_query

    if q.message.chat.id != ADMIN_CHAT_ID:
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

    if u.effective_chat.id != ADMIN_CHAT_ID:
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
# ОТМЕНА ОПРОСА
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
