#core/payments.py
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import ContextTypes
from core.db import increment_vip_tokens

# Show purchase options
async def purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✨ 1 Generation - 100 Stars", callback_data="buy_1")],
        [InlineKeyboardButton("✨ 5 Generations - 400 Stars", callback_data="buy_5")],
        [InlineKeyboardButton("✨ 10 Generations - 700 Stars", callback_data="buy_10")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🛒 Choose a credit pack to purchase using Telegram Stars:",
        reply_markup=reply_markup
    )

# Handle inline button callback to trigger invoice
async def handle_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id

    pack_mapping = {
        "buy_1": (1, 100),
        "buy_5": (5, 400),
        "buy_10": (10, 700)
    }

    pack_key = query.data
    if pack_key not in pack_mapping:
        await query.edit_message_text("❌ Invalid pack selected.")
        return

    generations, price = pack_mapping[pack_key]

    title = f"{generations} AI Image Generation{'s' if generations > 1 else ''}"
    payload = f"gen_{generations}_{chat_id}_{os.urandom(4).hex()}"
    prices = [LabeledPrice(label=title, amount=price)]

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=f"Upscale or enhance {generations} image(s) using AI.",
        payload=payload,
        provider_token="",  # Leave empty for Telegram Stars
        currency="XTR",
        prices=prices,
        start_parameter=f"buy_gen_{generations}",
        is_flexible=False
    )

# Pre-checkout (must approve all payments)
async def pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

# Handle payment confirmation
async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload

    if payload.startswith("gen_"):
        parts = payload.split("_")
        generations = int(parts[1]) if len(parts) > 1 else 1
    else:
        generations = 1

    telegram_id = update.effective_user.id
    increment_vip_tokens(telegram_id, generations)

    await update.message.reply_text(
        f"✅ Payment successful! You've been credited with {generations} generation(s)."
    )
