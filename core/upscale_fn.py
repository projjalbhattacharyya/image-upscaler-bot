import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import torch
from PIL import Image
from torchvision.transforms.functional import to_tensor, to_pil_image

from core.bsrgan.rrdbnet_arch import RRDBNet

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = None

MAX_INPUT_DIM = 4096       # Reject anything above this
SAFE_OUTPUT_DIM = 8192     # Downscale input if upscaled version would exceed this
MAX_FINAL_DIM = 6000       # Final image must not exceed this in either width or height
TELEGRAM_MAX_SUM = 10000   # Telegram: width + height must be ≤ 10000

def load_model():
    global model
    if model is None:
        weights_path = os.path.join("core", "bsrgan", "BSRGAN.pth")
        model = RRDBNet(in_nc=3, out_nc=3, nf=64, nb=23, sf=4)
        model.load_state_dict(torch.load(weights_path, map_location=device), strict=True)
        model.eval()
        model = model.to(device)

def process_tile(tile_tensor):
    """Run a single tile through the model."""
    with torch.no_grad():
        output = model(tile_tensor).clamp(0, 1)
    return output

def upscale_image(input_path: str, output_path: str, tile_size: int = 512, tile_overlap: int = 8):
    """
    Upscales an image using tiling to prevent OOM, 
    while keeping output within Telegram and size limits.
    """
    try:
        load_model()

        # Load image
        image = Image.open(input_path).convert("RGB")
        w, h = image.size
        print(f"[📥 INPUT] Original size: {w}x{h}")

        # Reject too large input
        if w > MAX_INPUT_DIM or h > MAX_INPUT_DIM:
            raise ValueError(f"❌ Input too large: {w}x{h} > {MAX_INPUT_DIM}px limit.")

        # Downscale if output would exceed safe limit
        if w * 4 > SAFE_OUTPUT_DIM or h * 4 > SAFE_OUTPUT_DIM:
            scale_factor = SAFE_OUTPUT_DIM / max(w, h)
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            image = image.resize((new_w, new_h), Image.LANCZOS)
            w, h = image.size

        img_tensor = to_tensor(image).unsqueeze(0).to(device)

        _, _, h, w = img_tensor.shape
        scale = 4  # Model scale factor

        # Prepare output tensor
        output_tensor = torch.zeros(
            (1, 3, h * scale, w * scale), device=device
        )
        weight_map = torch.zeros_like(output_tensor)

        # Iterate over tiles
        for y in range(0, h, tile_size - tile_overlap):
            for x in range(0, w, tile_size - tile_overlap):
                tile = img_tensor[:, :, y:y+tile_size, x:x+tile_size]
                sr_tile = process_tile(tile)

                out_y = y * scale
                out_x = x * scale
                oh, ow = sr_tile.shape[2], sr_tile.shape[3]

                output_tensor[:, :, out_y:out_y+oh, out_x:out_x+ow] += sr_tile
                weight_map[:, :, out_y:out_y+oh, out_x:out_x+ow] += 1

        # Normalize and clamp
        output_tensor /= weight_map
        output_tensor = output_tensor.clamp(0, 1)

        # Convert to PIL
        sr_image = to_pil_image(output_tensor.squeeze(0).cpu())
        final_w, final_h = sr_image.size
        print(f"[📤 OUTPUT BEFORE LIMIT] {final_w}x{final_h}")

        # Step 1: Apply MAX_FINAL_DIM limit
        if final_w > MAX_FINAL_DIM or final_h > MAX_FINAL_DIM:
            resize_factor = MAX_FINAL_DIM / max(final_w, final_h)
            new_w = int(final_w * resize_factor)
            new_h = int(final_h * resize_factor)
            sr_image = sr_image.resize((new_w, new_h), Image.LANCZOS)
            final_w, final_h = sr_image.size
            print(f"[⚠ FINAL RESIZE] Resized to: {new_w}x{new_h} due to MAX_FINAL_DIM")

        # Step 2: Apply Telegram's width+height limit
        if (final_w + final_h) > TELEGRAM_MAX_SUM:
            resize_factor = TELEGRAM_MAX_SUM / (final_w + final_h)
            new_w = int(final_w * resize_factor)
            new_h = int(final_h * resize_factor)
            sr_image = sr_image.resize((new_w, new_h), Image.LANCZOS)
            final_w, final_h = sr_image.size
            print(f"[⚠ TELEGRAM RESIZE] Resized to: {new_w}x{new_h} to meet width+height ≤ {TELEGRAM_MAX_SUM}")

        # Final log
        print(f"[✅ FINAL OUTPUT] {final_w}x{final_h}")

        # Save output
        sr_image.save(output_path, format="JPEG")

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
