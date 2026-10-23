import asyncio
import json
import os
import random
import sqlite3
import time
import hmac
import hashlib
from urllib.parse import parse_qsl
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
import uvicorn

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()
DEV_MODE = os.getenv("DEV_MODE", "0").lower() in {"1", "true", "yes"}
PORT = int(os.getenv("PORT", "8000"))
DATA_DIR = Path(os.getenv("DATA_DIR", "."))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "ludoman.sqlite3"
WEB_DIR = Path(__file__).parent / "web"

CASES = [
    {"id": "starter", "name": "Starter Case", "cost": 100, "emoji": "📦", "description": "Первый шаг"},
    {"id": "premium", "name": "Premium Case", "cost": 250, "emoji": "💎", "description": "Больше редких предметов"},
    {"id": "daily", "name": "Daily Case", "cost": 0, "emoji": "🎁", "description": "Бесплатный кейс"},
]

# Only virtual demo items in this starter build. Real Telegram gifts/NFTs are not delivered by this code.
REWARDS = {
    "starter": [
        {"name": "Зелёный куб", "emoji": "🟩", "rarity": "Обычный", "weight": 65, "value": 40},
        {"name": "Неоновая монета", "emoji": "🪙", "rarity": "Редкий", "weight": 25, "value": 100},
        {"name": "Золотая жаба", "emoji": "🐸", "rarity": "Эпический", "weight": 9, "value": 250},
        {"name": "Корона LUDOMAN", "emoji": "👑", "rarity": "Легендарный", "weight": 1, "value": 1000},
    ],
    "premium": [
        {"name": "Кристалл", "emoji": "🔮", "rarity": "Обычный", "weight": 50, "value": 100},
        {"name": "Звёздный подарок", "emoji": "🌟", "rarity": "Редкий", "weight": 32, "value": 250},
        {"name": "NFT-статуэтка (демо)", "emoji": "🗿", "rarity": "Эпический", "weight": 15, "value": 600},
        {"name": "Золотая корона", "emoji": "👑", "rarity": "Легендарный", "weight": 3, "value": 2000},
    ],
    "daily": [
        {"name": "Счастливая лягушка", "emoji": "🐸", "rarity": "Обычный", "weight": 70, "value": 25},
        {"name": "Мини-подарок", "emoji": "🎁", "rarity": "Редкий", "weight": 25, "value": 75},
        {"name": "Неоновый талисман", "emoji": "✨", "rarity": "Эпический", "weight": 5, "value": 200},
    ],
}

app = FastAPI(title="LUDOMAN Case API")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
dp = Dispatcher()
bot = Bot(BOT_TOKEN) if BOT_TOKEN else None


def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL DEFAULT '',
            first_name TEXT NOT NULL DEFAULT '',
            balance INTEGER NOT NULL DEFAULT 1000,
            created_at INTEGER NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            emoji TEXT NOT NULL,
            rarity TEXT NOT NULL,
            case_id TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS openings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            case_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            rarity TEXT NOT NULL,
            cost INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS daily_claims (
            telegram_id INTEGER PRIMARY KEY,
            claimed_at INTEGER NOT NULL
        )""")


def validate_init_data(init_data: str) -> dict:
    if not BOT_TOKEN:
        raise HTTPException(503, "BOT_TOKEN is not configured")
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            raise ValueError("missing hash")
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated, received_hash):
            raise ValueError("invalid signature")
        auth_date = int(parsed.get("auth_date", "0"))
        if abs(int(time.time()) - auth_date) > 86400:
            raise ValueError("expired initData")
        user = json.loads(parsed.get("user", "{}"))
        telegram_id = int(user["id"])
        return {
            "id": telegram_id,
            "username": user.get("username", ""),
            "first_name": user.get("first_name", "Игрок"),
        }
    except Exception as exc:
        raise HTTPException(401, "Telegram authorization failed") from exc


def get_user(authorization: str | None):
    if DEV_MODE and not authorization:
        return {"id": 999000001, "username": "demo_player", "first_name": "Демо"}
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(401, "Открой приложение через Telegram")
    return validate_init_data(authorization[4:])


def ensure_user(user):
    with connect_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, first_name, balance, created_at) VALUES (?, ?, ?, 1000, ?)",
            (user["id"], user.get("username", ""), user.get("first_name", "Игрок"), int(time.time()))
        )
        db.execute(
            "UPDATE users SET username=?, first_name=? WHERE telegram_id=?",
            (user.get("username", ""), user.get("first_name", "Игрок"), user["id"])
        )


def weighted_reward(case_id):
    rewards = REWARDS[case_id]
    return random.choices(rewards, weights=[r["weight"] for r in rewards], k=1)[0]


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/config")
def config():
    return {"dev_mode": DEV_MODE, "app_name": "LUDOMAN Case"}


@app.get("/api/me")
def me(authorization: str | None = Header(default=None)):
    user = get_user(authorization)
    ensure_user(user)
    with connect_db() as db:
        row = db.execute("SELECT balance FROM users WHERE telegram_id=?", (user["id"],)).fetchone()
        count = db.execute("SELECT COUNT(*) AS n FROM inventory WHERE telegram_id=?", (user["id"],)).fetchone()["n"]
    return {"id": user["id"], "first_name": user["first_name"], "username": user["username"],
            "balance": row["balance"], "inventory_count": count}


@app.get("/api/cases")
def cases():
    return {"cases": CASES}


@app.get("/api/inventory")
def inventory(authorization: str | None = Header(default=None)):
    user = get_user(authorization)
    ensure_user(user)
    with connect_db() as db:
        rows = db.execute(
            "SELECT id, item_name, emoji, rarity, case_id, created_at FROM inventory WHERE telegram_id=? ORDER BY id DESC LIMIT 100",
            (user["id"],)
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


@app.get("/api/history")
def history(authorization: str | None = Header(default=None)):
    user = get_user(authorization)
    ensure_user(user)
    with connect_db() as db:
        rows = db.execute(
            "SELECT case_id, item_name, rarity, cost, created_at FROM openings WHERE telegram_id=? ORDER BY id DESC LIMIT 20",
            (user["id"],)
        ).fetchall()
    return {"history": [dict(r) for r in rows]}


class OpenRequest(BaseModel):
    case_id: str


@app.post("/api/open")
def open_case(body: OpenRequest, authorization: str | None = Header(default=None)):
    user = get_user(authorization)
    ensure_user(user)
    case = next((c for c in CASES if c["id"] == body.case_id), None)
    if not case:
        raise HTTPException(404, "Кейс не найден")

    now = int(time.time())
    with connect_db() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT balance FROM users WHERE telegram_id=?", (user["id"],)).fetchone()
        if not row:
            raise HTTPException(401, "Пользователь не найден")
        if row["balance"] < case["cost"]:
            raise HTTPException(400, "Недостаточно монет")
        if body.case_id == "daily":
            claim = db.execute("SELECT claimed_at FROM daily_claims WHERE telegram_id=?", (user["id"],)).fetchone()
            if claim and now - claim["claimed_at"] < 86400:
                raise HTTPException(400, "Бесплатный кейс доступен раз в 24 часа")
            db.execute("INSERT INTO daily_claims(telegram_id, claimed_at) VALUES (?, ?) ON CONFLICT(telegram_id) DO UPDATE SET claimed_at=excluded.claimed_at",
                       (user["id"], now))
        reward = weighted_reward(body.case_id)
        db.execute("UPDATE users SET balance=balance-? WHERE telegram_id=?", (case["cost"], user["id"]))
        db.execute("INSERT INTO inventory(telegram_id,item_name,emoji,rarity,case_id,created_at) VALUES(?,?,?,?,?,?)",
                   (user["id"], reward["name"], reward["emoji"], reward["rarity"], body.case_id, now))
        db.execute("INSERT INTO openings(telegram_id,case_id,item_name,rarity,cost,created_at) VALUES(?,?,?,?,?,?)",
                   (user["id"], body.case_id, reward["name"], reward["rarity"], case["cost"], now))
        new_balance = db.execute("SELECT balance FROM users WHERE telegram_id=?", (user["id"],)).fetchone()["balance"]
    return {"reward": {k: reward[k] for k in ("name", "emoji", "rarity", "value")},
            "balance": new_balance, "case": case["name"]}


@dp.message(CommandStart())
async def start(message: Message):
    if not WEBAPP_URL:
        await message.answer(
            "🐸 Добро пожаловать в LUDOMAN Case!\n\n"
            "Mini App ещё не настроена. Добавь публичный HTTPS-адрес приложения в WEBAPP_URL."
        )
        return
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎁 Открыть LUDOMAN Case", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )
    await message.answer(
        "🐸 Добро пожаловать в LUDOMAN Case!\nОткрывай демо-кейсы, собирай виртуальные предметы и пополняй коллекцию.",
        reply_markup=keyboard
    )


async def run_bot():
    if bot:
        await dp.start_polling(bot)


async def run_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    init_db()
    if bot:
        await asyncio.gather(run_api(), run_bot())
    else:
        await run_api()


if __name__ == "__main__":
    asyncio.run(main())
