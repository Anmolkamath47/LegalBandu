import os
import uuid
import logging
from typing import Tuple, Optional
from ..config import settings
from .ai_service import is_gemini_configured

logger = logging.getLogger("legalbandu.images")

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "images"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

MIME_TYPE_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def save_image_file(file_bytes: bytes, original_filename: str) -> Tuple[str, str, str]:
    """
    Saves uploaded image file to disk and returns (stored_filename, file_path, image_url).
    """
    ext = os.path.splitext(original_filename)[1].lower()
    if not ext or ext not in SUPPORTED_IMAGE_EXTENSIONS:
        ext = ".png"

    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    image_url = f"/api/images/{unique_name}"
    return unique_name, file_path, image_url


def extract_dialogue_from_image(
    file_path: str,
    original_filename: str,
    deal_title: str = "",
) -> str:
    """
    Performs multimodal OCR on an uploaded conversation screenshot, handwritten note,
    or document image using Google Gemini Vision (gemini-3.5-flash-lite).
    Faithfully transcribes dialogue turns, timestamps, and terms with zero dummy data.
    """
    ext = os.path.splitext(original_filename)[1].lower()
    mime_type = MIME_TYPE_MAP.get(ext, "image/png")

    if not is_gemini_configured():
        logger.info("Gemini API key not configured; returning image receipt placeholder.")
        return f"[Image uploaded: {original_filename}. Gemini API key required for automatic OCR extraction.]"

    try:
        with open(file_path, "rb") as f:
            image_data = f.read()

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        prompt = f"""You are Legalbandu's AI multimodal OCR and document transcription engine.
Analyze this uploaded image (such as a WhatsApp chat screenshot, message thread, handwritten note, price estimate, or commercial memo) for the deal '{deal_title}'.

INSTRUCTIONS:
1. Extract ALL text, timestamps, numbers, and dialogue turns faithfully with 100% accuracy.
2. DO NOT fabricate, hallucinate, or insert dummy data.
3. If this is a chat screenshot (e.g. WhatsApp, SMS, Telegram, iMessage):
   Format each message turn as:
   [Timestamp if visible] Sender Name: Message content
   If no timestamp is visible, format as:
   Sender Name: Message content
4. If this is a handwritten note, invoice, or paper agreement:
   Transcribe all agreed terms, deliverables, prices, timelines, and responsibilities clearly line-by-line.
5. If the text is in an Indian language (e.g. Kannada, Hindi, Telugu, Tamil, Marathi):
   Provide the original script dialogue, followed by the English translation underneath each turn.

Return strictly the extracted dialogue or text with no extraneous conversational filler."""

        for candidate_model in [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"]:
            try:
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=[
                        types.Part.from_bytes(data=image_data, mime_type=mime_type),
                        prompt,
                    ],
                )
                if response.text and len(response.text.strip()) > 5:
                    logger.info(f"Successfully extracted OCR dialogue from {original_filename} via {candidate_model}")
                    return response.text.strip()
            except Exception as candidate_err:
                logger.warning(f"Candidate model {candidate_model} failed for image OCR: {candidate_err}")
                continue

        return f"[Image uploaded: {original_filename}. Text could not be extracted automatically.]"

    except Exception as e:
        logger.error(f"Error extracting dialogue from image {original_filename}: {e}", exc_info=True)
        return f"[Image uploaded: {original_filename}. OCR error: {str(e)}]"
