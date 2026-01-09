import asyncio
import logging
import os
import random
import string
import datetime
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import threading

BOT_TOKEN = "8464882605:AAGFAYMmgytLzSdzYWobSnrdT5uYf1YfOKw"
CHANNEL_USERNAME = "@feikDiq"
CHANNEL_ID = -1001234567890
ADMIN_ID = 7760606749
PWA_URL = "https://diia-bot-pwa.твой-username.repl.co"  # Замени на свой Replit адрес после Run
RULES_URL = "https://telegra.ph/твоє_посилання_на_правила"
INSTRUCTION_URL = "https://telegra.ph/твоє_посилання_на_інструкцію_оплати"
SUPPORT_USERNAME = "@твій_підтримка"
DB_FILE = "users.db"
PHOTOS_DIR = "photos"
RECEIPTS_DIR = "receipts"
STATIC_DIR = "static"

os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

flask_app = Flask(__name__, static_folder=STATIC_DIR)
CORS(flask_app)

@flask_app.route("/photos/<filename>")
def photos(filename):
    return send_from_directory(PHOTOS_DIR, filename)

@flask_app.route("/get_data")
async def get_data():
    code = request.args.get("code")
    if not code:
        return jsonify({"fio": "Невірний код", "birthdate": "", "photo_url": ""})

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT fio, birthdate, photo_path, expiry_time, active FROM users WHERE code=?", (code,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return jsonify({"fio": "Невірний код або термін дії закінчився", "birthdate": "", "photo_url": ""})

            fio, birthdate, photo_path, expiry, active = row

            if active == 0 or (expiry and datetime.datetime.now().timestamp() > expiry):
                return jsonify({"fio": "ПЕРІОД ПОДПИСКИ ЗАВЕРШЕНО", "birthdate": "", "photo_url": ""})

            photo_url = f"/photos/{os.path.basename(photo_path)}" if photo_path else ""
            return jsonify({"fio": fio, "birthdate": birthdate, "photo_url": photo_url})

@flask_app.route("/", defaults={"path": ""})
@flask_app.route("/<path:path>")
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(STATIC_DIR, path)):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                fio TEXT,
                birthdate TEXT,
                photo_path TEXT,
                code TEXT,
                subscription_type TEXT,
                expiry_time REAL,
                active INTEGER DEFAULT 1
            )
        ''')
        await db.commit()

class States(StatesGroup):
    subscribed_check = State()
    fio = State()
    birthdate = State()
    photo = State()
    choose_subscription = State()
    payment_method = State()
    waiting_card = State()
    waiting_receipt = State()

def generate_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

async def send_code_message(user_id: int, sub_type: str = "test"):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT code FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            code = row[0] if row else generate_code()
    text = (
        f"🎉 Ваша {'тестова ' if sub_type == 'test' else ''}підписка активна{' на 30 хвилин' if sub_type == 'test' else ''}!\n\n"
        f"🔑 Код для входу: {code}\n\n"
        f"🌐 Щоб увійти, перейдіть за посиланням:\n{PWA_URL}\n\n"
        "❗️ Не відкривайте посилання в Telegram\n"
        "❗️ Скопіюйте його та відкрийте у браузері\n\n"
        "Дякуємо, що скористалися нашим сервісом!"
    )
    await bot.send_message(user_id, text)

# ================== Весь функционал бота (полный) ==================
# (Весь твой оригинальный код хендлеров — от cmd_start до cmd_reset — вставь сюда, как был в твоём старом bot.py)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
