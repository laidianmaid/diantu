import os
import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE = os.getenv("BACKEND_URL", "http://backend:8000/api/v1")


async def fetch_shops(params: dict | None = None) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{API_BASE}/shops", params=params or {})
        return r.json() if r.status_code == 200 else []


async def ai_chat(message: str) -> tuple[str, list[int]]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{API_BASE}/ai/chat", json={"message": message})
        if r.status_code == 200:
            data = r.json()
            return data["reply"], data.get("highlighted_shop_ids", [])
    return "AI 暂时无法回应，请稍后再试。", []


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "☕ 欢迎使用「来点妹抖吗？」！\n\n"
        "/shops — 查看所有妹抖店\n"
        "/open — 查看营业中的妹抖店\n"
        "直接发消息 — AI 推荐"
    )


async def list_shops_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shops = await fetch_shops()
    if not shops:
        await update.message.reply_text("暂无店铺数据。")
        return
    text = "☕ 所有妹抖店：\n\n"
    for s in shops:
        score = f"{s['score']:.1f}" if s.get('score') else "—"
        text += f"• {s['name']} [{s['color']}] 评分:{score}\n"
    await update.message.reply_text(text)


async def open_shops_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shops = await fetch_shops({"status": "open"})
    if not shops:
        await update.message.reply_text("目前没有营业中的妹抖店。")
        return
    text = "🟢 营业中：\n\n"
    for s in shops:
        text += f"• {s['name']}\n"
    await update.message.reply_text(text)


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    await update.message.chat.send_action("typing")
    reply, ids = await ai_chat(msg)
    if ids:
        reply += f"\n\n🗺 高亮店铺 ID: {', '.join(map(str, ids))}"
    await update.message.reply_text(reply)


def main():
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN not set, bot disabled.")
        return
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shops", list_shops_cmd))
    app.add_handler(CommandHandler("open", open_shops_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
