#!/usr/bin/env python3
"""
SAFEGUARD V6 - AD NETWORK EDITION
Features: Group Protection, Trending Sales, & GLOBAL BROADCAST SYSTEM
"""

import os
import time
import asyncio
import threading
import requests
import asyncpg
from dotenv import load_dotenv
from flask import Flask

# Telegram Imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- 1. CONFIGURATION ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ETH_MAIN = os.getenv("ETH_MAIN", "").lower()
SOL_MAIN = os.getenv("SOL_MAIN", "")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = os.getenv("ADMIN_ID")
DOCS = os.getenv("DOCS_URL")
TWITTER = os.getenv("TWITTER_URL")

# --- 2. PRICING ---
TREND_PLANS = {
    "slot1": {"name": "🥇 Trending Spot #1", "price": 1500},
    "slot2": {"name": "🥈 Trending Spot #2", "price": 1000},
    "fast":  {"name": "⚡ Fast-Track Listing", "price": 500}
}

# --- 3. FLASK SERVER ---
flask_app = Flask(__name__)
@flask_app.route("/")
def health(): return "SAFEGUARD NETWORK ACTIVE 🟢", 200
def run_web(): flask_app.run(host="0.0.0.0", port=8080)

# --- 4. DATABASE ENGINE ---
pool = None
async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            # Table to store groups (The Ad Network)
            await conn.execute("CREATE TABLE IF NOT EXISTS cp_groups (chat_id TEXT PRIMARY KEY, title TEXT, portal_active BOOLEAN, joined_at BIGINT)")
            # Table for revenue
            await conn.execute("CREATE TABLE IF NOT EXISTS cp_payments (id SERIAL PRIMARY KEY, telegram_id TEXT, amount_usd DECIMAL, service_type TEXT, created_at BIGINT)")
        print("✅ Safeguard Database Linked")
    except Exception as e: print(f"⚠️ DB Error: {e}")

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
            "🔰 **Safeguard V6.0**\n\n"
            "The ultimate bot for crypto groups! Protection & Ad Network.\n\n"
            "`/setup`  -  **Create Portal (Protect Group)**\n"
            "`/trend`  -  **Boost your Token**\n\n"
            "👇 **Initialize:**"
        ),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

# --- THE PORTAL (How we get into groups) ---
async def setup_portal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type == "private":
        await update.message.reply_text("❌ Use this command inside a Group.")
        return

    # SAVE GROUP ID TO DATABASE (This builds your Ad Network)
    if pool:
        try:
            await pool.execute(
                "INSERT INTO cp_groups (chat_id, title, portal_active, joined_at) VALUES ($1, $2, TRUE, $3) ON CONFLICT (chat_id) DO UPDATE SET title = $2",
                str(update.effective_chat.id), update.effective_chat.title, int(time.time())
            )
        except: pass

    kb = [[InlineKeyboardButton("Tap to Verify 🟢", callback_data="verify_human")]]
    await update.message.reply_text(
        "🛡 **PORTAL ACTIVATED**\n\nNew members must click below to speak.\n*Safeguard is now monitoring this channel.*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

async def verify_human(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("✅ Verified! Welcome.", show_alert=True)

# --- THE MONEY (Trending Sales) ---
async def trend_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message if update.message else update.callback_query.message
    kb = []
    for k, v in TREND_PLANS.items():
        kb.append([InlineKeyboardButton(f"{v['name']} - ${v['price']}", callback_data=f"buy_{k}")])

    caption = (
        "📈 **TRENDING FAST-TRACK**\n\n"
        "Push your token to our massive network of groups.\n"
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

    await update.message.reply_text("✅ **PAYMENT SUBMITTED.**\n\nTrending Team is verifying. Boost will start in 15 mins.")
    if ADMIN_ID:
        await context.bot.send_message(ADMIN_ID, f"💰 **SAFEGUARD REVENUE:** {tx} from @{update.effective_user.username}")

# --- THE WEAPON (Broadcast Ad to All Groups) ---
async def broadcast_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only Admin can run this
    if str(update.effective_user.id) != str(ADMIN_ID): return

    try:
        # Usage: /broadcast_ad https://link.com MESSAGE...
        args = context.args
        if len(args) < 2:
            return await update.message.reply_text("❌ Usage: `/broadcast_ad <LINK> <MESSAGE>`")

        link = args[0]
        message = " ".join(args[1:])

        ad_text = (
            f"🚨 **SPONSORED TRENDING ALERT** 🚨\n\n"
            f"{message}\n\n"
            f"🚀 **View Chart:** {link}\n"
            f"⚡ *Verified by IceGods Safeguard*"
        )

        await update.message.reply_text("📣 **Initializing Network Broadcast...**")

        # 1. Fetch all groups from DB
        if pool:
            groups = await pool.fetch("SELECT chat_id FROM cp_groups")
            success_count = 0
            fail_count = 0

            for g in groups:
                chat_id = g['chat_id']
                try:
                    await context.bot.send_message(chat_id, ad_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
                    success_count += 1
                    await asyncio.sleep(0.1) # Anti-flood speed limit
                except Exception as e:
                    # If kicked, maybe remove from DB?
                    fail_count += 1

            await update.message.reply_text(f"✅ **CAMPAIGN COMPLETE.**\n\n🎯 Targets: {success_count}\n❌ Failed: {fail_count}")
        else:
            await update.message.reply_text("❌ Database not connected.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Critical Error: {e}")

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
    # THE WEAPON COMMAND
    app.add_handler(CommandHandler("broadcast_ad", broadcast_ad))

    app.add_handler(CallbackQueryHandler(verify_human, pattern="verify_human"))
    app.add_handler(CallbackQueryHandler(payment_handler, pattern="buy_"))

    print("🚀 SAFEGUARD V6 NETWORK LIVE...")
    app.run_polling()

if __name__ == "__main__":
    main()
