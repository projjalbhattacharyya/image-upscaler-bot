import os
from telegram import Update, BotCommand
from telegram.ext import ContextTypes
from core.db import register_user, get_user_generations, get_referral_count

# Define menu commands
MENU_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("profile", "View your profile"),
    BotCommand("purchase", "Upgrade or purchase features"),
    BotCommand("refer", "Refer and earn rewards"),
    BotCommand("help", "Show help info"),
    BotCommand("bots", "Explore my other bots")
]

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    args = context.args

    referrer_id = None
    if args and args[0].isdigit():
        referrer_id = int(args[0])

    await register_user(telegram_id, referrer_id, context.bot)
  
    await update.message.reply_text(
        "<b>Welcome! 👋</b>\n"
        "🖼 Send me an image and I’ll upscale it for you.\n\n"
        "🎁 <i>New users get 2 free generations to start with!</i>",
        parse_mode="HTML"
    )

# /profile command
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = get_user_generations(telegram_id)

    if not user:
        await update.message.reply_text("❌ You are not registered. Please use /start first.")
        return

    # Get user's Telegram name
    user_name = (
        update.effective_user.full_name
        or update.effective_user.username
        or "there"
    )

    free_gen = user["free_tokens"]
    vip_gen = user["vip_tokens"]
    referral_count = get_referral_count(telegram_id)

    await update.message.reply_text(
        f"👋 Hello, *{user_name}*!\n\n"
        f"📊 *Your Upscaling Profile:*\n"
        f"🆓 Free Tokens Remaining: `{free_gen}`\n"
        f"💳 VIP Tokens Remaining: `{vip_gen}`\n\n"
        f"👥 Referrals: `{referral_count}`\n\n"
        f"🚀 Keep sending images to get stunning upscaled results!\n"
        f"💡 Use /refer to earn more generations by inviting friends.",
        parse_mode="Markdown"
    )

# /refer command
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    refer_link = f"https://t.me/{bot_username}?start={telegram_id}"
    
    await update.message.reply_text(
        f"🔗 <b>Invite your friends!</b>\n"
        f"Share this link and you'll get 1 Free Token when someone joins using it:\n\n"
        f"<code>{refer_link}</code>",
        parse_mode="HTML"
    )


# /bots command
async def bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 More awesome bots coming soon! Stay tuned 🚀")

# /terms command
async def terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 <b>Terms of Service</b>\n\n"
        "1. This bot uses AI to enhance or upscale images.\n"
        "2. Your images are processed temporarily and deleted after use.\n"
        "3. Generations are non-refundable unless an error occurred.\n"
        "4. Payments are handled via Telegram Stars.\n",
        parse_mode="HTML"
    )

# /paysupport command
async def paysupport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💬 <b>Payment Support</b>\n\n"
        "If you have any issues with your purchase, contact: @your_support_handle",
        parse_mode="HTML"
    )

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>🆘 Help Guide</b>\n\n"
        "Here's what you can do with this bot:\n\n"
        "📤 *Send an image* – I’ll upscale it using AI\n"
        "👤 /profile – Check your remaining *Tokens*\n"
        "💳 /purchase – Buy more *Tokens* using Telegram Stars\n"
        "👥 /refer – Invite friends and earn Free Tokens\n"
        "🤖 /bots – Discover more of my AI bots\n"
        "📜 /terms – Read terms of service\n"
        "💬 /paysupport – Contact support for payment issues\n",
        parse_mode="HTML"
    )

# Set menu commands on startup
async def set_menu_commands(app):
    await app.bot.set_my_commands(MENU_COMMANDS)