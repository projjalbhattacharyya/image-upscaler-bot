# services/tasks.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.celery_app import celery
import requests
from core.db import decrement_generation
from core.upscale_fn import upscale_image

BOT_TOKEN = os.getenv("BOT_TOKEN")


@celery.task(name="services.tasks.upscale_image_task")
def upscale_image_task(input_path: str, output_path: str, chat_id: str):
    telegram_id = int(chat_id)

    try:
        # 1. Run the upscaling
        upscale_image(input_path, output_path)

        # 2. Decrement user's generation count
        usage_type = decrement_generation(telegram_id)

        # 3. Send image via Telegram API
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(output_path, "rb") as photo:
            caption = "✅ Here is your upscaled image!\n"

            if usage_type == "vip":
                caption += "💎 1 *VIP Token* used!"
            elif usage_type == "free":
                caption += "🎁 1 Free Token used!"

            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': 'Markdown'  # You can change to 'HTML' if needed
            }
            files = {'photo': photo}
            response = requests.post(url, data=data, files=files)
            print(f"[Telegram] {response.status_code} | {response.text}")

    except Exception as e:
        print(f"[❌ ERROR] {e}")
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {'chat_id': chat_id, 'text': '❌ Failed to send the upscaled image.'}
            requests.post(url, data=data)
        except Exception as notify_err:
            print(f"[❌ Notify Fail] {notify_err}")

    finally:
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception as cleanup_err:
            print(f"[WARN] Cleanup failed: {cleanup_err}")
