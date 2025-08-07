import os
import uuid

from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from core.db import get_user_generations
from services.tasks import upscale_image_task
from services.celery_app import celery

router = APIRouter()

TEMP_DIR = os.path.abspath("temp")
os.makedirs(TEMP_DIR, exist_ok=True)

@router.get("/", summary="Home", tags=["Utility"])
async def read_root():
    return {
        "message": "👋 Welcome to the Image Upscaler API!",
        "endpoints": {
            "POST /upscale": "Upload an image to upscale",
            "GET /result/{task_id}": "Get the upscaled result using task ID",
            "GET /health": "Check server health",
            "GET /docs": "Swagger UI",
            "GET /redoc": "ReDoc documentation"
        }
    }

@router.get("/health", summary="Health Check", tags=["Utility"])
async def health_check():
    return {"status": "ok"}

@router.post(
    "/upscale",
    summary="Upscale an image",
    description="Upload a JPEG or PNG image and queue it for AI upscaling.",
    response_description="Returns a task ID to check result later",
    responses={
        200: {"description": "Task queued successfully"},
        400: {"description": "Invalid file type"},
        500: {"description": "Internal server error"},
    }
)
async def upscale_endpoint(
    file: UploadFile = File(..., description="The image file to upscale (JPEG or PNG)"),
    chat_id: str = Form(..., description="Telegram chat ID to send result back to")
):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

    uid = uuid.uuid4().hex
    input_path = os.path.join(TEMP_DIR, f"input_{uid}.jpg")
    output_path = os.path.join(TEMP_DIR, f"output_{uid}.jpg")

    with open(input_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Check if user has vip generations
    user_data = get_user_generations(int(chat_id))  # chat_id = telegram_id
    user_is_vip = user_data and user_data["vip_tokens"] > 0

    # Choose queue based on generation type
    queue_name = "vip" if user_is_vip else "free"

    task = upscale_image_task.apply_async(args=[input_path, output_path, chat_id], queue=queue_name)

    return {
        "status": "queued",
        "task_id": task.id,
        "message": f"Image queued in the {queue_name} queue"
    }

@router.get(
    "/result/{task_id}",
    summary="Check upscale result by task ID",
    description="Poll the result of an upscaling task using the task ID",
    responses={
        200: {"description": "Upscaled image or task status"},
        404: {"description": "Task result not available or file missing"},
    }
)
def get_upscale_result(task_id: str, background_tasks: BackgroundTasks):
    result = celery.AsyncResult(task_id)

    if result.state == "PENDING":
        return {"status": "pending"}

    elif result.state == "SUCCESS":
        output_path = result.result
        if output_path and os.path.exists(output_path):
            background_tasks.add_task(delete_file, output_path)
            return FileResponse(output_path, media_type="image/jpeg", filename="upscaled.jpg")
        return {"status": "done", "error": "file_missing"}

    elif result.state == "FAILURE":
        return {"status": "failed", "error": str(result.result)}

    return {"status": result.state.lower()}

def delete_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"[WARN] Failed to delete {path}: {e}")
