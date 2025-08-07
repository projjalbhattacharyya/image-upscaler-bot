# bot/handlers.py
import os
import uuid
import aiohttp

from telegram import Update
from telegram.error import Forbidden
from telegram.ext import ContextTypes

from core.db import get_user_generations, decrement_generation

FASTAPI_URL = "http://localhost:8000/upscale"

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ I only respond to images. Please send me a photo.")

async def safe_reply(message, text, **kwargs):
    """Send a reply and handle if bot is blocked."""
    try:
        await message.reply_text(text, **kwargs)
    except Forbidden:
        print(f"[WARN] Bot blocked by user {message.chat_id}")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user_generations(telegram_id)

    if not user:
        await safe_reply(update.message, "❌ You are not registered. Please use /start first.")
        return

    free_gen = user["free_tokens"]
    vip_gen = user["vip_tokens"]

    if free_gen <= 0 and vip_gen <= 0:
        await safe_reply(
            update.message,
            "⚠️ You've used all your available *Tokens*.\n\n"
            "💳 <b>Please /purchase more credits to continue using the bot.</b>\n\n"
            "💡 You can also /refer friends to earn free *Tokens*!",
            parse_mode="HTML"
        )
        return

    await safe_reply(update.message, "🔄 Uploading image and queuing for upscaling...")

    os.makedirs("temp", exist_ok=True)
    unique_id = f"{telegram_id}_{update.message.message_id}_{uuid.uuid4().hex}"
    input_path = f"temp/input_{unique_id}.jpg"

    try:
        # Step 1: Download image
        photo = update.message.photo[-1]
        file = await photo.get_file()
        await file.download_to_drive(input_path)

        # Step 2: Send image + chat_id to FastAPI
        async with aiohttp.ClientSession() as session:
            with open(input_path, "rb") as image_file:
                form_data = aiohttp.FormData()
                form_data.add_field("file", image_file, filename="upload.jpg", content_type="image/jpeg")
                form_data.add_field("chat_id", str(update.effective_chat.id))  # Pass chat_id

                async with session.post(FASTAPI_URL, data=form_data) as resp:
                    if resp.status != 200:
                        raise Exception(f"FastAPI error: {await resp.text()}")

        # Build single combined message
        msg = "✅ Image queued successfully. You’ll receive the result here when it’s ready.\n\n"

        if vip_gen > 0:
            msg += "💎 Using *VIP Token* — your request will be prioritized for faster processing!"
        elif free_gen > 0:
            msg += "🎁 Using *Free Token*."

        await safe_reply(update.message, msg, parse_mode="Markdown")
        # ⚠️ DO NOT decrement generation now — let Celery do it after successful processing

    except Exception as e:
        await safe_reply(update.message, f"❌ Failed to queue image: {str(e)}")

    finally:
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception as cleanup_err:
            print(f"[WARN] Cleanup failed: {cleanup_err}")
