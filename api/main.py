from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

# FastAPI app metadata
app = FastAPI(
    title="Image Upscaler API",
    version="1.0.0",
    description="A simple API that uses Real-ESRGAN to upscale low-resolution images. Supports JPEG and PNG formats."
)

# Allow CORS (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)

# User (Telegram) ──▶ Bot (bot.py) ──▶ POST /upscale ──▶ FastAPI (main.py) ──▶ upscale.py ──▶ Result image
#                                                                                     ▲
#                                                                                     └── RealESRGAN Model
