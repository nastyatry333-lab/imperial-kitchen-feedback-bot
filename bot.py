import os
import logging
from datetime import datetime

from telegram import InlineKeyboardButton as B
from telegram import InlineKeyboardMarkup as M
from telegram import Update

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
)


# =========================================================
# НАСТРОЙКИ
# =========================================================

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])

GIS = "https://go.2gis.com/qE6oV"
SITE = "https://imperialkitchen.kz"
SUPPORT = "https://t.me/imperialkitchen95"

DATA_DIR = "/data"
PERSISTENCE_FILE = os.path.join(
    DATA_DIR,
    "imperial_bot_data.pkl",
)

os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    ),
)


# =========================================================
# КЛИЕНТСКИЕ КНОПКИ
# =========================================================

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


# =========================================================
# КНОПКИ ОБРАЩЕНИЯ В ОСНОВНОЙ КАРТОЧКЕ
# =========================================================

def admin_new_buttons(user_id):
    return M([
        [
            B(
                "🟡 Взять в работу",
                callback_data=f"admin_work:{user_id}",
            )
        ],
        [
            B(
                "💬 Ответить клиенту",
                callback_data=f"admin_reply:{user_id}",
            )
        ],
        [
            B(
                "✅ Закрыть обращение",
                callback_data=f"admin_close:{user_id}",
            )
        ],
    ])


def admin_work_buttons(user_id):
    return M([
        [
            B(
                "💬 Ответить клиенту",
                callback_data=f"admin_reply:{user_id}",
            )
        ],
        [
            B(
                "✅ Закрыть обращение",
                callback_data=f"admin_close:{user_id}",
            )
        ],
    ])


def admin_closed_buttons(user_id):
    return M([
        [
            B(
                "💬 Ответить клиенту",
                callback_data=f"admin_reply:{user_id}",
            )
        ],
    ])


# =========================================================
# АДМИН-ПАНЕЛЬ
# =========================================================

def admin_menu():
    return M([
        [
            B(
                "📊 Статистика",
                callback_data="panel_stats",
            )
        ],
        [
            B(
                "🔴 Новые",
                callback_data="panel_new",
            ),
            B(
                "🟡 В работе",
                callback_data="panel_work",
            ),
        ],
        [
            B(
                "📋 Все активные",
                callback_data="panel_active",
            )
        ],
        [
            B(
                "⭐ Последние оценки",
                callback_data="panel_ratings",
            )
        ],
        [
            B(
                "📚 История клиента",
                callback_data="panel_history",
            )
        ],
        [
            B(
                "🔄 Обновить",
                callback_data="panel_home",
            )
        ],
    ])


def back_admin():
    return M([
        [
            B(
                "⬅️ Назад в админ-панель",
                callback_data="panel_home",
            )
        ]
    ])


def ticket_list_keyboard(items, list_type):
    rows = []

    for item in reversed(items[-10:]):
        ticket = item.get("ticket", "?")
        order = item.get("order", "без номера")
        status = item.get("status", "new")

        icon = {
            "new": "🔴",
            "work": "🟡",
            "closed": "✅",
        }.get(status, "⚪")

        label = f"{icon} {ticket} • {order}"

        rows.append([
            B(
                label,
                callback_data=(
                    f"ticket:{ticket}:{list_type}"
                ),
            )
        ])

    rows.append([
        B(
            "⬅️ Назад в админ-панель",
            callback_data="panel_home",
        )
    ])

    return M(rows)


def ticket_card_keyboard(
    ticket,
    user_id,
    status,
    back_to,
):
    rows = []

    if status == "new":
        rows.append([
            B(
                "🟡 Взять в работу",
                callback_data=(
                    f"ticket_work:{ticket}:{back_to}"
                ),
            )
        ])

    if status in ("new", "work", "closed"):
        rows.append([
            B(
                "💬 Ответить клиенту",
                callback_data=(
                    f"ticket_reply:{ticket}:{back_to}"
                ),
            )
        ])

    if status in ("new", "work"):
        rows.append([
            B(
                "✅ Закрыть обращение",
                callback_data=(
                    f"ticket_close:{ticket}:{back_to}"
                ),
            )
        ])

    rows.append([
        B(
            "⬅️ Назад к списку",
            callback_data=f"backlist:{back_to}",
        )
    ])

    rows.append([
        B(
            "🏠 Админ-панель",
            callback_data="panel_home",
        )
    ])

    return M(rows)


# =========================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# =========================================================

def is_admin(update):
    return (
        update.effective_chat is not None
        and update.effective_chat.id == ADMIN_CHAT_ID
    )


def next_ticket_number(context):
    number = int(
        context.bot_data.get(
            "ticket_counter",
            0,
        )
    ) + 1

    context.bot_data["ticket_counter"] = number

    return f"IK-{number:04d}"


def save_rating(context, user_id, rating):
    ratings = context.bot_data.setdefault(
        "ratings",
        [],
    )

    ratings.append({
        "user_id": user_id,
        "rating": rating,
        "date": datetime.now().isoformat(),
    })


def customer_complaint_count(context, user_id):
    history = context.bot_data.get(
        "customer_history",
        {},
    )

    return len(
        history.get(
            str(user_id),
            [],
        )
    )


def save_complaint_history(
    context,
    user_id,
    complaint,
):
    history = context.bot_data.setdefault(
        "customer_history",
        {},
    )

    history.setdefault(
        str(user_id),
        [],
    ).append(complaint)


def update_history_status(
    context,
    user_id,
    ticket,
    status,
):
    history = context.bot_data.setdefault(
        "customer_history",
        {},
    )

    items = history.get(
        str(user_id),
        [],
    )

    for item in reversed(items):
        if item.get("ticket") == ticket:
            item["status"] = status
            break


def status_name(status):
    names = {
        "new": "🔴 НОВОЕ",
        "work": "🟡 В РАБОТЕ",
        "closed": "✅ РЕШЕНО",
    }

    return names.get(status, status)


def find_complaint_by_ticket(context, ticket):
    complaints = context.bot_data.get(
        "complaints",
        {},
    )

    for message_id, complaint in complaints.items():
        if complaint.get("ticket") == ticket:
            return message_id, complaint

    return None, None


def format_date(value):
    if not value:
        return "не указано"

    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return value


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "🍣 Imperial Kitchen\n\n"
        "Спасибо, что выбрали нас ❤️\n\n"
        "Нам важно, чтобы каждый заказ радовал вас. "
        "Оцените свой заказ — это займёт меньше минуты.",
        reply_markup=home(),
    )


# =========================================================
# КЛИЕНТСКАЯ ОЦЕНКА
# =========================================================

async def review(update, context):
    context.user_data.clear()

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Как вам заказ Imperial Kitchen?\n\n"
        "Поставьте, пожалуйста, оценку:",
        reply_markup=stars(),
    )


async def rating(update, context):
    query = update.callback_query
    await query.answer()

    value = int(query.data[1:])

    context.user_data["rating"] = value

    save_rating(
        context,
        update.effective_user.id,
        value,
    )

    if value >= 4:
        context.user_data.clear()

        await query.edit_message_text(
            "❤️ Спасибо за высокую оценку!\n\n"
            "Нам будет очень приятно, если вы "
            "поделитесь своим впечатлением "
            "об Imperial Kitchen:",
            reply_markup=M([
                [
                    B(
                        "⭐ Оставить отзыв в 2GIS",
                        url=GIS,
                    )
                ],
                [
                    B(
                        "🌐 Оставить отзыв на сайте",
                        url=SITE,
                    )
                ],
                [
                    B(
                        "🔄 Оценить другой заказ",
                        callback_data="review",
                    )
                ],
            ]),
        )

        return

    context.user_data["stage"] = "order"

    await query.edit_message_text(
        "😔 Спасибо, что сообщили нам.\n\n"
        "Мы хотим разобраться в ситуации.\n\n"
        "Напишите, пожалуйста, номер вашего заказа.",
        reply_markup=M([
            [
                B(
                    "Не знаю номер заказа",
                    callback_data="unknown",
                )
            ]
        ]),
    )


async def unknown(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["order"] = "не указан"
    context.user_data["stage"] = "reason"

    await query.edit_message_text(
        "Что именно пошло не так?",
        reply_markup=reasons(),
    )


async def reason(update, context):
    query = update.callback_query
    await query.answer()

    reason_names = {
        "x_food": "Качество блюда",
        "x_delivery": "Доставка",
        "x_order": "Ошибка в заказе",
        "x_service": "Обслуживание",
        "x_other": "Другое",
    }

    context.user_data["reason"] = reason_names.get(
        query.data,
        "Другое",
    )

    context.user_data["stage"] = "comment"

    await query.edit_message_text(
        "Расскажите, пожалуйста, подробнее, "
        "что произошло.\n\n"
        "Напишите сообщение ниже. "
        "После этого можно будет приложить фотографию."
    )


# =========================================================
# ТЕКСТОВЫЕ СООБЩЕНИЯ
# =========================================================

async def text_message(update, context):

    # Ответ администратора клиенту
    if is_admin(update):
        reply_state = context.chat_data.get(
            "admin_reply_to"
        )

        if reply_state:
            user_id = reply_state["user_id"]
            ticket = reply_state.get(
                "ticket",
                "",
            )

            text = update.message.text.strip()

            try:
                title = "💬 Ответ Imperial Kitchen"

                if ticket:
                    title += f"\n🎫 Обращение {ticket}"

                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"{title}\n\n"
                        f"{text}\n\n"
                        "Если вам нужно дополнить обращение, "
                        "вы можете написать нашей "
                        "службе поддержки."
                    ),
                )

                await update.message.reply_text(
                    "✅ Ответ отправлен клиенту."
                )

            except Exception:
                logging.exception(
                    "Не удалось отправить ответ клиенту"
                )

                await update.message.reply_text(
                    "❌ Не удалось отправить "
                    "сообщение клиенту."
                )

            context.chat_data.pop(
                "admin_reply_to",
                None,
            )

            return

    stage = context.user_data.get("stage")

    if stage == "order":
        context.user_data["order"] = (
            update.message.text.strip()
        )

        context.user_data["stage"] = "reason"

        await update.message.reply_text(
            "Спасибо. Что именно пошло не так?",
            reply_markup=reasons(),
        )

        return

    if stage == "comment":
        context.user_data["comment"] = (
            update.message.text.strip()
        )

        context.user_data["stage"] = "photo"

        await update.message.reply_text(
            "Если у вас есть фотография проблемы, "
            "отправьте её сюда.\n\n"
            "Если фотографии нет — нажмите кнопку ниже.",
            reply_markup=M([
                [
                    B(
                        "➡️ Отправить без фото",
                        callback_data="nophoto",
                    )
                ]
            ]),
        )


# =========================================================
# СОЗДАНИЕ ОБРАЩЕНИЯ
# =========================================================

def admin_complaint_text(
    update,
    context,
    ticket,
    previous,
):
    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else "не указан"
    )

    if previous == 0:
        history_text = "Первое обращение"
    else:
        history_text = (
            f"Ранее обращался: {previous} раз"
        )

    return (
        "🚨 ОБРАЩЕНИЕ — IMPERIAL KITCHEN\n\n"
        f"🎫 № обращения: {ticket}\n"
        "📌 Статус: 🔴 НОВОЕ\n\n"
        f"⭐ Оценка: "
        f"{context.user_data.get('rating', '?')}/5\n"
        f"🧾 Заказ: "
        f"{context.user_data.get('order', 'не указан')}\n"
        f"⚠️ Причина: "
        f"{context.user_data.get('reason', 'не указана')}\n\n"
        f"👤 Клиент: {user.full_name or 'не указано'}\n"
        f"📱 Telegram: {username}\n"
        f"🆔 User ID: {user.id}\n"
        f"📚 История: {history_text}\n\n"
        "💬 Комментарий:\n"
        f"{context.user_data.get('comment', 'нет')}"
    )


async def finish_complaint(
    update,
    context,
    photo=None,
):
    user_id = update.effective_user.id

    previous = customer_complaint_count(
        context,
        user_id,
    )

    ticket = next_ticket_number(context)

    complaint = {
        "ticket": ticket,
        "user_id": user_id,
        "rating": context.user_data.get(
            "rating"
        ),
        "order": context.user_data.get(
            "order",
            "не указан",
        ),
        "reason": context.user_data.get(
            "reason",
            "не указана",
        ),
        "comment": context.user_data.get(
            "comment",
            "нет",
        ),
        "status": "new",
        "date": datetime.now().isoformat(),
    }

    admin_message = await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_complaint_text(
            update,
            context,
            ticket,
            previous,
        ),
        reply_markup=admin_new_buttons(
            user_id
        ),
    )

    complaint["admin_message_id"] = (
        admin_message.message_id
    )

    complaints = context.bot_data.setdefault(
        "complaints",
        {},
    )

    complaints[
        str(admin_message.message_id)
    ] = complaint

    save_complaint_history(
        context,
        user_id,
        complaint.copy(),
    )

    if photo:
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=photo,
            caption=(
                f"📸 Фото к обращению {ticket}"
            ),
        )

    context.user_data.clear()

    client_text = (
        "🙏 Спасибо, что рассказали нам о ситуации.\n\n"
        f"🎫 Номер вашего обращения: {ticket}\n\n"
        "Ваше обращение передано руководству "
        "Imperial Kitchen. Мы обязательно разберёмся.\n\n"
        "Если вопрос срочный, вы можете сразу "
        "написать нашей службе поддержки."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            client_text,
            reply_markup=finish(),
        )
    else:
        await update.message.reply_text(
            client_text,
            reply_markup=finish(),
        )


async def no_photo(update, context):
    query = update.callback_query
    await query.answer()

    if context.user_data.get("stage") == "photo":
        await finish_complaint(
            update,
            context,
        )


async def photo_message(update, context):
    if context.user_data.get("stage") != "photo":
        return

    await finish_complaint(
        update,
        context,
        update.message.photo[-1].file_id,
    )


# =========================================================
# СТАРЫЕ КАРТОЧКИ — В РАБОТУ
# =========================================================

async def admin_work(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    user_id = int(
        query.data.split(":")[1]
    )

    message_id = str(
        query.message.message_id
    )

    complaints = context.bot_data.setdefault(
        "complaints",
        {},
    )

    complaint = complaints.get(
        message_id,
        {},
    )

    ticket = complaint.get(
        "ticket",
        "неизвестно",
    )

    text = query.message.text.replace(
        "📌 Статус: 🔴 НОВОЕ",
        "📌 Статус: 🟡 В РАБОТЕ",
    )

    await query.edit_message_text(
        text,
        reply_markup=admin_work_buttons(
            user_id
        ),
    )

    complaint["status"] = "work"

    update_history_status(
        context,
        user_id,
        ticket,
        "work",
    )


# =========================================================
# СТАРЫЕ КАРТОЧКИ — ЗАКРЫТЬ
# =========================================================

async def admin_close(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    user_id = int(
        query.data.split(":")[1]
    )

    message_id = str(
        query.message.message_id
    )

    complaints = context.bot_data.setdefault(
        "complaints",
        {},
    )

    complaint = complaints.get(
        message_id,
        {},
    )

    ticket = complaint.get(
        "ticket",
        "неизвестно",
    )

    text = query.message.text

    text = text.replace(
        "📌 Статус: 🔴 НОВОЕ",
        "📌 Статус: ✅ РЕШЕНО",
    )

    text = text.replace(
        "📌 Статус: 🟡 В РАБОТЕ",
        "📌 Статус: ✅ РЕШЕНО",
    )

    await query.edit_message_text(
        text,
        reply_markup=admin_closed_buttons(
            user_id
        ),
    )

    complaint["status"] = "closed"

    update_history_status(
        context,
        user_id,
        ticket,
        "closed",
    )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Обращение {ticket} отмечено "
                "как решённое.\n\n"
                "Спасибо, что помогаете Imperial Kitchen "
                "становиться лучше ❤️"
            ),
        )
    except Exception:
        logging.exception(
            "Не удалось уведомить клиента"
        )


# =========================================================
# СТАРЫЕ КАРТОЧКИ — ОТВЕТИТЬ
# =========================================================

async def admin_reply(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    user_id = int(
        query.data.split(":")[1]
    )

    message_id = str(
        query.message.message_id
    )

    complaint = context.bot_data.get(
        "complaints",
        {},
    ).get(
        message_id,
        {},
    )

    context.chat_data["admin_reply_to"] = {
        "user_id": user_id,
        "ticket": complaint.get(
            "ticket",
            "",
        ),
    }

    await query.message.reply_text(
        "✍️ Напишите ответ клиенту "
        "следующим сообщением.\n\n"
        "Я отправлю его клиенту "
        "от имени Imperial Kitchen.\n\n"
        "Для отмены отправьте /cancelreply"
    )


async def cancel_reply(update, context):
    if not is_admin(update):
        return

    if context.chat_data.get(
        "admin_reply_to"
    ):
        context.chat_data.pop(
            "admin_reply_to",
            None,
        )

        await update.message.reply_text(
            "❌ Отправка ответа отменена."
        )
    else:
        await update.message.reply_text(
            "Сейчас нет активного ответа клиенту."
        )


# =========================================================
# СТАТИСТИКА
# =========================================================

def statistics_text(context):
    ratings = context.bot_data.get(
        "ratings",
        [],
    )

    complaints = context.bot_data.get(
        "complaints",
        {},
    )

    total = len(ratings)

    if total:
        average = sum(
            int(x.get("rating", 0))
            for x in ratings
        ) / total
    else:
        average = 0

    counts = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
    }

    for item in ratings:
        value = int(
            item.get(
                "rating",
                0,
            )
        )

        if value in counts:
            counts[value] += 1

    new_count = sum(
        1
        for x in complaints.values()
        if x.get("status") == "new"
    )

    work_count = sum(
        1
        for x in complaints.values()
        if x.get("status") == "work"
    )

    closed_count = sum(
        1
        for x in complaints.values()
        if x.get("status") == "closed"
    )

    reasons_count = {}

    for item in complaints.values():
        reason = item.get("reason")

        if reason:
            reasons_count[reason] = (
                reasons_count.get(
                    reason,
                    0,
                ) + 1
            )

    if reasons_count:
        sorted_reasons = sorted(
            reasons_count.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        reasons_text = "\n".join(
            f"• {name}: {count}"
            for name, count in sorted_reasons
        )
    else:
        reasons_text = "Пока нет данных"

    return (
        "📊 СТАТИСТИКА — IMPERIAL KITCHEN\n\n"
        f"⭐ Всего оценок: {total}\n"
        f"📈 Средняя оценка: {average:.2f}/5\n\n"
        "Распределение оценок:\n"
        f"⭐ 5 — {counts[5]}\n"
        f"⭐ 4 — {counts[4]}\n"
        f"⭐ 3 — {counts[3]}\n"
        f"⭐ 2 — {counts[2]}\n"
        f"⭐ 1 — {counts[1]}\n\n"
        "🚨 ОБРАЩЕНИЯ\n\n"
        f"🔴 Новые: {new_count}\n"
        f"🟡 В работе: {work_count}\n"
        f"✅ Решено: {closed_count}\n"
        f"📦 Всего обращений: {len(complaints)}\n\n"
        "⚠️ Причины обращений:\n"
        f"{reasons_text}"
    )


async def stats(update, context):
    if not is_admin(update):
        return

    await update.message.reply_text(
        statistics_text(context)
    )


# =========================================================
# ИСТОРИЯ
# =========================================================

async def history_command(update, context):
    if not is_admin(update):
        return

    if not context.args:
        await update.message.reply_text(
            "📚 Чтобы посмотреть историю клиента:\n\n"
            "/history USER_ID\n\n"
            "Например:\n"
            "/history 123456789"
        )
        return

    user_id = context.args[0]

    history = context.bot_data.get(
        "customer_history",
        {},
    ).get(
        str(user_id),
        [],
    )

    if not history:
        await update.message.reply_text(
            "По этому клиенту обращений пока нет."
        )
        return

    lines = [
        "📚 ИСТОРИЯ КЛИЕНТА",
        f"🆔 User ID: {user_id}",
        f"📦 Всего обращений: {len(history)}",
        "",
    ]

    for item in reversed(history[-10:]):
        lines.extend([
            f"🎫 {item.get('ticket', '?')}",
            f"⭐ {item.get('rating', '?')}/5",
            f"🧾 Заказ: {item.get('order', 'не указан')}",
            f"⚠️ {item.get('reason', 'не указана')}",
            f"📌 {status_name(item.get('status', 'new'))}",
            "",
        ])

    await update.message.reply_text(
        "\n".join(lines)
    )


# =========================================================
# ГЛАВНАЯ АДМИН-ПАНЕЛЬ
# =========================================================

def admin_dashboard_text(context):
    ratings = context.bot_data.get(
        "ratings",
        [],
    )

    complaints = context.bot_data.get(
        "complaints",
        {},
    )

    if ratings:
        average = sum(
            int(x.get("rating", 0))
            for x in ratings
        ) / len(ratings)
    else:
        average = 0

    new_count = sum(
        1
        for x in complaints.values()
        if x.get("status") == "new"
    )

    work_count = sum(
        1
        for x in complaints.values()
        if x.get("status") == "work"
    )

    closed_count = sum(
        1
        for x in complaints.values()
        if x.get("status") == "closed"
    )

    return (
        "👑 IMPERIAL KITCHEN — АДМИН\n\n"
        f"⭐ Средняя оценка: {average:.2f}/5\n"
        f"📊 Всего оценок: {len(ratings)}\n\n"
        f"🔴 Новые: {new_count}\n"
        f"🟡 В работе: {work_count}\n"
        f"✅ Решено: {closed_count}\n\n"
        "Выберите нужный раздел:"
    )


async def admin_panel(update, context):
    if not is_admin(update):
        return

    await update.message.reply_text(
        admin_dashboard_text(context),
        reply_markup=admin_menu(),
    )


async def panel_home(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    await query.edit_message_text(
        admin_dashboard_text(context),
        reply_markup=admin_menu(),
    )


async def panel_stats(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    await query.edit_message_text(
        statistics_text(context),
        reply_markup=back_admin(),
    )


# =========================================================
# СПИСКИ ОБРАЩЕНИЙ
# =========================================================

def get_complaints(context, wanted=None):
    complaints = context.bot_data.get(
        "complaints",
        {},
    )

    items = []

    for item in complaints.values():
        status = item.get(
            "status",
            "new",
        )

        if wanted == "new":
            if status != "new":
                continue

        elif wanted == "work":
            if status != "work":
                continue

        elif wanted == "active":
            if status == "closed":
                continue

        items.append(item)

    return items


async def show_ticket_list(
    query,
    context,
    list_type,
):
    if list_type == "new":
        title = "🔴 НОВЫЕ ОБРАЩЕНИЯ"
        items = get_complaints(
            context,
            "new",
        )

    elif list_type == "work":
        title = "🟡 ОБРАЩЕНИЯ В РАБОТЕ"
        items = get_complaints(
            context,
            "work",
        )

    else:
        title = "📋 ВСЕ АКТИВНЫЕ ОБРАЩЕНИЯ"
        items = get_complaints(
            context,
            "active",
        )

    if not items:
        await query.edit_message_text(
            f"{title}\n\n"
            "👌 Здесь пока нет обращений.",
            reply_markup=back_admin(),
        )
        return

    await query.edit_message_text(
        f"{title}\n\n"
        "Нажмите на обращение, "
        "чтобы открыть его карточку:",
        reply_markup=ticket_list_keyboard(
            items,
            list_type,
        ),
    )


async def panel_new(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    await show_ticket_list(
        query,
        context,
        "new",
    )


async def panel_work(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    await show_ticket_list(
        query,
        context,
        "work",
    )


async def panel_active(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    await show_ticket_list(
        query,
        context,
        "active",
    )


async def back_to_list(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    list_type = query.data.split(
        ":",
        1,
    )[1]

    await show_ticket_list(
        query,
        context,
        list_type,
    )


# =========================================================
# ОТКРЫТИЕ ОБРАЩЕНИЯ ИЗ ПАНЕЛИ
# =========================================================

def ticket_card_text(complaint):
    ticket = complaint.get(
        "ticket",
        "?",
    )

    status = complaint.get(
        "status",
        "new",
    )

    return (
        "🎫 ОБРАЩЕНИЕ "
        f"{ticket}\n\n"
        f"📌 Статус: {status_name(status)}\n"
        f"🕐 Создано: "
        f"{format_date(complaint.get('date'))}\n\n"
        f"⭐ Оценка: "
        f"{complaint.get('rating', '?')}/5\n"
        f"🧾 Заказ: "
        f"{complaint.get('order', 'не указан')}\n"
        f"⚠️ Причина: "
        f"{complaint.get('reason', 'не указана')}\n"
        f"🆔 User ID: "
        f"{complaint.get('user_id', '?')}\n\n"
        "💬 Комментарий:\n"
        f"{complaint.get('comment', 'нет')}"
    )


async def open_ticket(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    parts = query.data.split(
        ":",
        2,
    )

    ticket = parts[1]
    back_to = parts[2]

    _, complaint = find_complaint_by_ticket(
        context,
        ticket,
    )

    if not complaint:
        await query.edit_message_text(
            "❌ Обращение не найдено.",
            reply_markup=back_admin(),
        )
        return

    await query.edit_message_text(
        ticket_card_text(
            complaint
        ),
        reply_markup=ticket_card_keyboard(
            ticket,
            complaint.get("user_id"),
            complaint.get(
                "status",
                "new",
            ),
            back_to,
        ),
    )


# =========================================================
# ВЗЯТЬ В РАБОТУ ИЗ ПАНЕЛИ
# =========================================================

async def ticket_work(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    parts = query.data.split(
        ":",
        2,
    )

    ticket = parts[1]
    back_to = parts[2]

    _, complaint = find_complaint_by_ticket(
        context,
        ticket,
    )

    if not complaint:
        await query.answer(
            "Обращение не найдено.",
            show_alert=True,
        )
        return

    complaint["status"] = "work"

    user_id = complaint.get(
        "user_id"
    )

    update_history_status(
        context,
        user_id,
        ticket,
        "work",
    )

    # Обновляем также исходную карточку, если возможно
    original_id = complaint.get(
        "admin_message_id"
    )

    if original_id:
        try:
            old_text = (
                "🚨 ОБРАЩЕНИЕ — IMPERIAL KITCHEN\n\n"
                f"🎫 № обращения: {ticket}\n"
                "📌 Статус: 🟡 В РАБОТЕ\n\n"
                f"⭐ Оценка: {complaint.get('rating', '?')}/5\n"
                f"🧾 Заказ: {complaint.get('order', 'не указан')}\n"
                f"⚠️ Причина: {complaint.get('reason', 'не указана')}\n\n"
                f"🆔 User ID: {user_id}\n\n"
                "💬 Комментарий:\n"
                f"{complaint.get('comment', 'нет')}"
            )

            await context.bot.edit_message_text(
                chat_id=ADMIN_CHAT_ID,
                message_id=original_id,
                text=old_text,
                reply_markup=admin_work_buttons(
                    user_id
                ),
            )
        except Exception:
            logging.exception(
                "Не удалось обновить исходную карточку"
            )

    await query.edit_message_text(
        ticket_card_text(
            complaint
        ),
        reply_markup=ticket_card_keyboard(
            ticket,
            user_id,
            "work",
            back_to,
        ),
    )


# =========================================================
# ЗАКРЫТЬ ИЗ ПАНЕЛИ
# =========================================================

async def ticket_close(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    parts = query.data.split(
        ":",
        2,
    )

    ticket = parts[1]
    back_to = parts[2]

    _, complaint = find_complaint_by_ticket(
        context,
        ticket,
    )

    if not complaint:
        await query.answer(
            "Обращение не найдено.",
            show_alert=True,
        )
        return

    complaint["status"] = "closed"

    user_id = complaint.get(
        "user_id"
    )

    update_history_status(
        context,
        user_id,
        ticket,
        "closed",
    )

    original_id = complaint.get(
        "admin_message_id"
    )

    if original_id:
        try:
            old_text = (
                "🚨 ОБРАЩЕНИЕ — IMPERIAL KITCHEN\n\n"
                f"🎫 № обращения: {ticket}\n"
                "📌 Статус: ✅ РЕШЕНО\n\n"
                f"⭐ Оценка: {complaint.get('rating', '?')}/5\n"
                f"🧾 Заказ: {complaint.get('order', 'не указан')}\n"
                f"⚠️ Причина: {complaint.get('reason', 'не указана')}\n\n"
                f"🆔 User ID: {user_id}\n\n"
                "💬 Комментарий:\n"
                f"{complaint.get('comment', 'нет')}"
            )

            await context.bot.edit_message_text(
                chat_id=ADMIN_CHAT_ID,
                message_id=original_id,
                text=old_text,
                reply_markup=admin_closed_buttons(
                    user_id
                ),
            )
        except Exception:
            logging.exception(
                "Не удалось обновить исходную карточку"
            )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Обращение {ticket} отмечено "
                "как решённое.\n\n"
                "Спасибо, что помогаете Imperial Kitchen "
                "становиться лучше ❤️"
            ),
        )
    except Exception:
        logging.exception(
            "Не удалось уведомить клиента"
        )

    await query.edit_message_text(
        ticket_card_text(
            complaint
        ),
        reply_markup=ticket_card_keyboard(
            ticket,
            user_id,
            "closed",
            back_to,
        ),
    )


# =========================================================
# ОТВЕТИТЬ ИЗ ПАНЕЛИ
# =========================================================

async def ticket_reply(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    parts = query.data.split(
        ":",
        2,
    )

    ticket = parts[1]

    _, complaint = find_complaint_by_ticket(
        context,
        ticket,
    )

    if not complaint:
        await query.answer(
            "Обращение не найдено.",
            show_alert=True,
        )
        return

    context.chat_data["admin_reply_to"] = {
        "user_id": complaint.get(
            "user_id"
        ),
        "ticket": ticket,
    }

    await query.message.reply_text(
        f"✍️ Ответ клиенту по обращению {ticket}\n\n"
        "Напишите следующим сообщением текст ответа.\n\n"
        "Для отмены отправьте /cancelreply"
    )


# =========================================================
# ПОСЛЕДНИЕ ОЦЕНКИ
# =========================================================

async def panel_ratings(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    ratings = context.bot_data.get(
        "ratings",
        [],
    )

    if not ratings:
        text = "⭐ Оценок пока нет."

    else:
        lines = [
            "⭐ ПОСЛЕДНИЕ ОЦЕНКИ",
            "",
        ]

        for item in reversed(
            ratings[-10:]
        ):
            value = int(
                item.get(
                    "rating",
                    0,
                )
            )

            user_id = item.get(
                "user_id",
                "?",
            )

            lines.append(
                f"{'⭐' * value} — "
                f"User ID: {user_id}"
            )

        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        reply_markup=back_admin(),
    )


# =========================================================
# ИСТОРИЯ ИЗ ПАНЕЛИ
# =========================================================

async def panel_history(update, context):
    query = update.callback_query

    if not is_admin(update):
        await query.answer(
            "Нет доступа.",
            show_alert=True,
        )
        return

    await query.answer()

    await query.edit_message_text(
        "📚 ИСТОРИЯ КЛИЕНТА\n\n"
        "Для просмотра истории отправьте:\n\n"
        "/history USER_ID\n\n"
        "User ID находится в карточке обращения.",
        reply_markup=back_admin(),
    )


# =========================================================
# ОТМЕНА
# =========================================================

async def cancel(update, context):
    context.user_data.clear()

    await update.message.reply_text(
        "Опрос отменён. Можно начать заново.",
        reply_markup=home(),
    )


# =========================================================
# ЗАПУСК
# =========================================================

def main():

    persistence = PicklePersistence(
        filepath=PERSISTENCE_FILE
    )

    application = (
        Application.builder()
        .token(TOKEN)
        .persistence(persistence)
        .build()
    )

    # Команды
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("cancel", cancel)
    )

    application.add_handler(
        CommandHandler(
            "cancelreply",
            cancel_reply,
        )
    )

    application.add_handler(
        CommandHandler("stats", stats)
    )

    application.add_handler(
        CommandHandler(
            "history",
            history_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            admin_panel,
        )
    )

    # Панель
    application.add_handler(
        CallbackQueryHandler(
            panel_home,
            pattern=r"^panel_home$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            panel_stats,
            pattern=r"^panel_stats$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            panel_new,
            pattern=r"^panel_new$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            panel_work,
            pattern=r"^panel_work$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            panel_active,
            pattern=r"^panel_active$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            panel_ratings,
            pattern=r"^panel_ratings$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            panel_history,
            pattern=r"^panel_history$",
        )
    )

    # Открытие обращения
    application.add_handler(
        CallbackQueryHandler(
            open_ticket,
            pattern=r"^ticket:[^:]+:[^:]+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            ticket_work,
            pattern=r"^ticket_work:[^:]+:[^:]+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            ticket_close,
            pattern=r"^ticket_close:[^:]+:[^:]+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            ticket_reply,
            pattern=r"^ticket_reply:[^:]+:[^:]+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            back_to_list,
            pattern=r"^backlist:[^:]+$",
        )
    )

    # Старые карточки обращений
    application.add_handler(
        CallbackQueryHandler(
            admin_work,
            pattern=r"^admin_work:\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            admin_reply,
            pattern=r"^admin_reply:\d+$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            admin_close,
            pattern=r"^admin_close:\d+$",
        )
    )

    # Клиент
    application.add_handler(
        CallbackQueryHandler(
            review,
            pattern=r"^review$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            rating,
            pattern=r"^r[1-5]$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            unknown,
            pattern=r"^unknown$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            reason,
            pattern=r"^x_",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            no_photo,
            pattern=r"^nophoto$",
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_message,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_message,
        )
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
