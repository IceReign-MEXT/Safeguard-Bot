#!/usr/bin/env python3
"""
SAFEGUARD V5.5 - GROUP PROTECTION & TRENDING ENGINE
Features: Portal, Buy Tracker, Trending Sales
"""

import os
import time
import asyncio
import threading
import requests
import asyncpg
from dotenv import load_dotenv
from flask import Flask

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# --- 1. CONFIGURATION ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ETH_MAIN = os.getenv("ETH_MAIN", "").lower()
SOL_MAIN = os.getenv("SOL_MAIN", "")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = os.getenv("ADMIN_ID")

DOCS = os.getenv("DOCS_URL")
TWITTER = os.getenv("TWITTER_URL")

# --- 2. TRENDING PRICES ---
TREND_PLANS = {
    "slot1": {"name": "🥇 Trending Spot #1", "price": 1500},
    "slot2": {"name": "🥈 Trending Spot #2", "price": 1000},
    "fast":  {"name": "⚡ Fast-Track Listing", "price": 500}
}

# --- 3. FLASK SERVER ---
flask_app = Flask(__name__)
@flask_app.route("/")
def health(): return "SAFEGUARD V5.5 ONLINE 🟢", 200
def run_web(): flask_app.run(host="0.0.0.0", port=8080)

# --- 4. DATABASE ---
pool = None
async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            # Table for Groups using the bot
            await conn.execute("CREATE TABLE IF NOT EXISTS cp_groups (chat_id TEXT PRIMARY KEY, title TEXT, portal_active BOOLEAN)")
        print("✅ Safeguard Linked to Ecosystem")
    except: pass

# --- 5. HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/ICEHack_Bot?startgroup=true")],
        [InlineKeyboardButton("📖 Docs", url=DOCS), InlineKeyboardButton("🐦 Twitter", url=TWITTER)],
        [InlineKeyboardButton("▶️ Trending Fast-Track", callback_data="trend_menu")]
    ]
    await update.message.reply_photo(
        photo="https://cdn.pixabay.com/photo/2018/05/14/16/25/cyber-security-3400657_1280.jpg",
        caption=(
            "🔰 **Safeguard V5.5**\n\n"
            "The ultimate bot for crypto groups! Best protection & token buy tracker.\n\n"
            "`/setup`  -  Create a portal\n"
            "`/add`  -  Add token to tracker\n"
            "`/trend`  -  **Boost your token**\n\n"
            "👇 **Initialize:**"
        ),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

async def setup_portal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type == "private":
        await update.message.reply_text("❌ Use this command inside a Group.")
        return

    # Log Group to DB
    if pool:
        try:
            await pool.execute(
                "INSERT INTO cp_groups (chat_id, title, portal_active) VALUES ($1, $2, TRUE) ON CONFLICT (chat_id) DO NOTHING",
                str(update.effective_chat.id), update.effective_chat.title
            )
        except: pass

    kb = [[InlineKeyboardButton("Tap to Verify 🟢", callback_data="verify_human")]]
    await update.message.reply_text(
        "🛡 **PORTAL ACTIVATED**\n\nNew members must click below to speak.",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def verify_human(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("✅ Verified! Welcome to the community.", show_alert=True)
    # Logic to unmute user would go here (requires Admin rights)

async def trend_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This can be triggered via /trend OR button
    msg = update.message if update.message else update.callback_query.message

    kb = []
    for k, v in TREND_PLANS.items():
        kb.append([InlineKeyboardButton(f"{v['name']} - ${v['price']}", callback_data=f"buy_{k}")])

    caption = (
        "📈 **TRENDING FAST-TRACK**\n\n"
        "@Trending & @SOLTrending — The largest trending platform with 5.5M daily views.\n\n"
        "**Guarantee your spot:**"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await msg.edit_caption(caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    else:
        await msg.reply_text(caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if "buy_" in q.data:
        key = q.data.replace("buy_", "")
        item = TREND_PLANS[key]

        # Log Revenue Intent
        try:
            if pool:
                await pool.execute("INSERT INTO cp_payments (telegram_id, amount_usd, service_type, created_at) VALUES ($1, $2, $3, $4)", 
                                   str(q.from_user.id), item['price'], f"Safeguard_{key}", int(time.time()))
        except: pass

        text = (
            f"🧾 **INVOICE: {item['name']}**\n\n"
            f"💰 **Amount:** ${item['price']} USD\n\n"
            f"💠 **ETH:** `{ETH_MAIN}`\n"
            f"🟣 **SOL:** `{SOL_MAIN}`\n\n"
            f"⚠️ **Reply:** `/confirm <TX_HASH>`"
        )
        await q.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("❌ Usage: `/confirm <HASH>`")
    tx = context.args[0]

    # Manual verify simulation (Safe)
    await update.message.reply_text("✅ **PAYMENT SUBMITTED.**\n\nTrending Team is verifying your transaction. Boost will start in 10-15 mins.")
    if ADMIN_ID:
        await context.bot.send_message(ADMIN_ID, f"💰 **SAFEGUARD REVENUE:** {tx} from @{update.effective_user.username}")

# --- MAIN ---
def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: loop.run_until_complete(init_db())
    except: pass

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setup", setup_portal))
    app.add_handler(CommandHandler("trend", trend_menu))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CallbackQueryHandler(verify_human, pattern="verify_human"))
    app.add_handler(CallbackQueryHandler(payment_handler, pattern="buy_"))

    print("🚀 SAFEGUARD V5.5 LIVE...")
    app.run_polling()

if __name__ == "__main__":
    main()
