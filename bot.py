import os, json, logging
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN=os.environ["BOT_TOKEN"]
ADMIN_SECRET=os.environ.get("ADMIN_SECRET","Imperial95Owner")
GIS_URL="https://go.2gis.com/qE6oV"
SITE_URL="https://imperialkitchen.kz"
ADMIN_FILE=Path("admin.json")
logging.basicConfig(level=logging.INFO)

def save_admin(chat_id):
    ADMIN_FILE.write_text(json.dumps({"chat_id":chat_id}),encoding="utf-8")

def get_admin():
    x=os.environ.get("ADMIN_CHAT_ID")
    if x:
        try: return int(x)
        except ValueError: pass
    try: return int(json.loads(ADMIN_FILE.read_text(encoding="utf-8"))["chat_id"])
    except Exception: return None

def kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ 1",callback_data="rating_1"),InlineKeyboardButton("⭐ 2",callback_data="rating_2"),InlineKeyboardButton("⭐ 3",callback_data="rating_3")],
        [InlineKeyboardButton("⭐ 4",callback_data="rating_4"),InlineKeyboardButton("⭐ 5",callback_data="rating_5")]
    ])

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🍣 Добро пожаловать в Imperial Kitchen!\n\nСпасибо, что выбрали нас ❤️\nНам очень важно узнать ваше мнение о заказе.\n\nПоставьте, пожалуйста, оценку:",reply_markup=kb())

async def admin(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0]!=ADMIN_SECRET:
        await update.message.reply_text("⛔ Неверный код администратора."); return
    save_admin(update.effective_chat.id)
    await update.message.reply_text(f"✅ Администратор подключён.\n\nВаш Telegram chat ID: {update.effective_chat.id}\nТеперь негативные отзывы будут приходить сюда.")

async def rating(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    v=int(q.data.split("_")[1]); context.user_data["rating"]=v
    if v>=4:
        context.user_data.clear()
        links=InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ Оставить отзыв в 2GIS",url=GIS_URL)],
            [InlineKeyboardButton("🌐 Оставить отзыв на сайте",url=SITE_URL)]
        ])
        await q.edit_message_text("❤️ Спасибо за высокую оценку!\n\nНам будет очень приятно, если вы поделитесь своим впечатлением об Imperial Kitchen. Выберите, где вам удобнее оставить отзыв:",reply_markup=links)
    else:
        context.user_data["waiting"]=True
        await q.edit_message_text("😔 Спасибо, что сообщили нам.\n\nРасскажите, пожалуйста, что произошло или что нам нужно улучшить.\n\nНапишите сообщение ниже — оно будет передано руководству Imperial Kitchen.")

async def comment(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting"): return
    u=update.effective_user; v=context.user_data.get("rating","?")
    username=f"@{u.username}" if u.username else "не указан"
    text=f"🚨 НОВЫЙ ОТЗЫВ IMPERIAL KITCHEN\n\n⭐ Оценка: {v}/5\n👤 Клиент: {u.full_name}\n📱 Telegram: {username}\n🆔 User ID: {u.id}\n\n💬 Комментарий:\n{update.message.text}"
    aid=get_admin()
    if aid:
        try:
            await context.bot.send_message(aid,text)
            await update.message.reply_text("🙏 Спасибо, что рассказали нам о ситуации.\n\nВаше сообщение передано руководству Imperial Kitchen. Мы обязательно обратим на него внимание.")
        except Exception:
            logging.exception("admin send failed")
            await update.message.reply_text("Спасибо за обратную связь. Пожалуйста, также напишите нам: @imperialkitchen95")
    else:
        await update.message.reply_text("Спасибо за обратную связь. Пожалуйста, также напишите нам: @imperialkitchen95")
    context.user_data.clear()

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("admin",admin))
    app.add_handler(CallbackQueryHandler(rating,pattern=r"^rating_[1-5]$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,comment))
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
