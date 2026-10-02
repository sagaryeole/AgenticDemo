import mimetypes
import re
from pathlib import Path

from google.adk.agents import Agent
from google.genai import types
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent28"  # lets AGENT28_MODEL_PROVIDER override the global choice
IMAGES = Path(__file__).resolve().parent / "images"
IMAGE_NAME = re.compile(r"[\w\-]+\.(?:png|jpe?g|webp)", re.IGNORECASE)


# A message to a model is a list of PARTS. Text is one kind of part; an image is another (bytes plus a type such as
# image/png). `adk run` only lets you type text, so this callback looks for image file names in what you typed
# (for example "receipt.png") and adds the image itself as an extra part, before the request goes to the model.
# In `adk web` you can attach an image with the paperclip button instead.
def attach_named_images(callback_context, llm_request):
    for content in llm_request.contents or []:
        if content.role != "user":
            continue
        parts = content.parts or []
        if any(p.inline_data or (p.text or "").startswith("[System note") for p in parts):
            continue  # this message already has its images (or notes) attached
        text = " ".join(p.text for p in parts if p.text)
        for name in IMAGE_NAME.findall(text):
            path = IMAGES / name
            if not path.exists():
                print(f"[image] {name} not found in {IMAGES.name}/")
                # Tell the model plainly. Without this line Gemini invented a whole menu for a missing menu.png.
                content.parts.append(types.Part(text=f"[System note: the file {name} was not found, so no image is attached.]"))
                continue
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            content.parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=mime))
            print(f"[image] attached {name} ({path.stat().st_size // 1024} KB, {mime})")
    return None


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="Answers questions about images.",
    instruction=(
        "You answer questions about the images the user shares. Describe only what you can actually see. "
        "If something is unclear or not visible in the image, say so instead of guessing. "
        "When the question involves numbers in the image, read them carefully and show the calculation."
    ),
    before_model_callback=attach_named_images,
)
