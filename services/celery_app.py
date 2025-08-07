#services/celery_app.py
from celery import Celery
import os
from dotenv import load_dotenv
import sys

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

celery = Celery(
    "upscaler",
    broker=os.getenv("REDIS_BROKER_URL"),
    backend=os.getenv("REDIS_RESULT_BACKEND")
)

import services.tasks
