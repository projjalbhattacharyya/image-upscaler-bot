import os; 
from dotenv import load_dotenv

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler, filters
from bot.handlers import handle_image, unknown
from bot.commands import start, profile, refer, bots, terms, paysupport, help_command, set_menu_commands, MENU_COMMANDS
from core.payments import purchase, handle_purchase_callback, pre_checkout_query, successful_payment_handler

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found. Please set it in your .env file.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Set persistent menu commands after bot initializes
    app.post_init = set_menu_commands

    # Register all bot commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("refer", refer))
    app.add_handler(CommandHandler("bots", bots))
    app.add_handler(CommandHandler("terms", terms))
    app.add_handler(CommandHandler("paysupport", paysupport))
    app.add_handler(CommandHandler("help", help_command))

    # Handle incoming images
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    # Handle payments
    app.add_handler(CommandHandler("purchase", purchase))
    app.add_handler(CallbackQueryHandler(handle_purchase_callback, pattern="^buy_"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_query))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # Handle unknown text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    # Run bot
    app.run_polling()
