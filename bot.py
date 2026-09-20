import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ["BOT_TOKEN"]

GIS_URL = "https://go.2gis.com/qE6oV"
SUPPORT_URL = "https://t.me/imperialkitchen95"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

WELCOME_TEXT = (
    "🍣 Добро пожаловать в Imperial Kitchen!\n\n"
    "Спасибо, что выбрали нас ❤️\n"
    "Нам очень важно узнать ваше мнение о заказе.\n\n"
    "Как вам всё понравилось?"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👍 Всё понравилось", callback_data="positive")],
        [InlineKeyboardButton("👎 Есть замечания", callback_data="negative")],
    ]
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "positive":
        keyboard = [[InlineKeyboardButton("⭐ Оставить отзыв в 2GIS", url=GIS_URL)]]
        text = (
            "❤️ Спасибо! Мы очень рады, что вам всё понравилось!\n\n"
            "Если у вас есть минутка, оставьте, пожалуйста, отзыв о нас в 2GIS. "
            "Ваш отзыв очень помогает Imperial Kitchen развиваться."
        )
    else:
        keyboard = [[InlineKeyboardButton("💬 Написать в поддержку", url=SUPPORT_URL)]]
        text = (
            "😔 Нам очень жаль, что что-то пошло не так.\n\n"
            "Мы хотим разобраться в ситуации и всё исправить. "
            "Пожалуйста, напишите нашей службе поддержки — мы обязательно рассмотрим ваше обращение."
        )

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(feedback, pattern="^(positive|negative)$"))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
