import os
import uuid
import re
import logging
from typing import Dict, Any, Tuple, Optional
from ..config import settings
from .ai_service import is_gemini_configured, analyze_conversation_with_gemini

logger = logging.getLogger("legalbandu.audio")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "audio")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".webm", ".flac"}


def save_audio_file(file_bytes: bytes, original_filename: str) -> Tuple[str, str, str]:
    """
    Saves uploaded audio file to disk and returns (stored_filename, file_path, audio_url).
    """
    ext = os.path.splitext(original_filename)[1].lower()
    if not ext or ext not in SUPPORTED_AUDIO_EXTENSIONS:
        ext = ".webm" if "webm" in original_filename.lower() else ".mp3"

    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    audio_url = f"/api/audio/{unique_name}"
    return unique_name, file_path, audio_url


def transcribe_audio_file(
    file_path: str,
    original_filename: str,
    deal_title: str = "",
    client_transcript: Optional[str] = None,
) -> str:
    """
    Transcribes audio call recording into dialogue format with speaker tags.
    Prioritizes:
    1. Client live transcript from in-browser speech recognition (if provided).
    2. Google Gemini multimodal audio transcription (gemini-3.5-transcribe + bilingual translation).
    3. Honest diagnostic state if no clear audio speech is found (strictly zero dummy/fabricated data).
    """
    if client_transcript and len(client_transcript.strip()) > 10:
        logger.info("Using high-fidelity client live speech transcription.")
        # Ensure speaker labels if missing
        lines = [l.strip() for l in client_transcript.splitlines() if l.strip()]
        if any(":" in l for l in lines):
            return client_transcript.strip()
        # Format lines into dialogue turns
        dialogue = []
        for idx, line in enumerate(lines):
            speaker = "Speaker 1 (Caller)" if idx % 2 == 0 else "Speaker 2 (Counterparty)"
            dialogue.append(f"{speaker}: {line}")
        return "\n".join(dialogue)

    # If Gemini is configured, use Gemini's audio transcription engine
    if is_gemini_configured():
        try:
            logger.info("Using Google Gemini multimodal API for call audio transcription.")
            ext = os.path.splitext(file_path)[1].lower()
            mime_map = {
                ".mp3": "audio/mp3",
                ".wav": "audio/wav",
                ".ogg": "audio/ogg",
                ".m4a": "audio/m4a",
                ".webm": "audio/webm",
                ".flac": "audio/flac",
                ".aac": "audio/aac",
            }
            mime_type = mime_map.get(ext, "audio/mp3")

            with open(file_path, "rb") as f:
                audio_data = f.read()

            from google import genai
            from google.genai import types
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            raw_transcription = None

            # 1. Primary: Specialized speech-to-text model (handles Kannada, Hindi, English, etc.)
            try:
                transcribe_res = client.models.generate_content(
                    model="gemini-3.5-transcribe",
                    contents=[types.Part.from_bytes(data=audio_data, mime_type=mime_type)],
                )
                if transcribe_res.candidates:
                    for part in transcribe_res.candidates[0].content.parts:
                        if hasattr(part, "audio_transcription") and part.audio_transcription:
                            raw_transcription = getattr(part.audio_transcription, "text", "") or str(part.audio_transcription)
                            if raw_transcription:
                                break
                        elif hasattr(part, "text") and part.text:
                            raw_transcription = part.text
                            if raw_transcription:
                                break
            except Exception as e_trans:
                logger.warning(f"gemini-3.5-transcribe notice: {e_trans}")

            # 2. Secondary fallback: Multimodal language models if transcribe model didn't return text
            if not raw_transcription:
                prompt_trans = (
                    f"Listen to this business call recording for the deal '{deal_title}'. "
                    "The conversation may be in Kannada, Hindi, Tamil, Telugu, English, or mixed languages. "
                    "Transcribe the conversation verbatim capturing all spoken words, numbers, prices, and commitments."
                )
                for candidate_model in [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"]:
                    try:
                        resp = client.models.generate_content(
                            model=candidate_model,
                            contents=[
                                types.Part.from_bytes(data=audio_data, mime_type=mime_type),
                                prompt_trans,
                            ],
                        )
                        if resp.text and len(resp.text.strip()) > 10:
                            raw_transcription = resp.text.strip()
                            break
                    except Exception as e_gen:
                        logger.debug(f"Candidate audio model {candidate_model} notice: {e_gen}")
                        continue

            # 3. If raw transcription was obtained, format and provide bilingual translation if regional language
            if raw_transcription and len(raw_transcription.strip()) > 5:
                logger.info("Raw audio transcription obtained. Generating bilingual dialogue formatting...")
                format_prompt = f"""You are Legalbandu's multilingual legal documentation assistant.
Below is the authentic verbatim transcript of a business call recording for the deal '{deal_title}':
\"\"\"
{raw_transcription.strip()}
\"\"\"

The audio may be spoken in Kannada, Hindi, Telugu, Tamil, Marathi, or English.
Please format this into structured conversational dialogue for formal agreement drafting:
1. If the speech is in an Indian language (e.g. Kannada):
   - Provide the Original Vernacular Dialogue in native script:
     Speaker 1: [Original speech in native script]
     Speaker 2: [Original speech in native script]
   - Provide the Faithful English Translation:
     Speaker 1: [Faithful English translation]
     Speaker 2: [Faithful English translation]
2. If the speech is in English:
   Speaker 1 (Caller): [Spoken text]
   Speaker 2 (Counterparty): [Spoken text]
3. Strictly preserve all numerical values, monetary amounts (INR, Lakhs, Crores), land/scope measurements (guntas, acres, square feet), deadlines, and deliverables.
4. Do NOT use markdown bold on speaker labels (use 'Speaker 1:' instead of '**Speaker 1:**').
"""
                for format_model in [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"]:
                    try:
                        fmt_res = client.models.generate_content(
                            model=format_model,
                            contents=format_prompt,
                        )
                        if fmt_res.text and len(fmt_res.text.strip()) > 20:
                            cleaned_dialogue = re.sub(r"\*\*(Speaker\s*\d+[^:*]*):\*\*", r"\1:", fmt_res.text.strip())
                            return cleaned_dialogue
                    except Exception as e_fmt:
                        logger.debug(f"Format model {format_model} notice: {e_fmt}")
                        continue

                # If formatting fails, return raw transcription directly
                return raw_transcription.strip()

        except Exception as err:
            logger.warning(f"Gemini audio transcription encountered error: {err}")

    # Honest diagnostic fallback when audio cannot be transcribed (strictly zero dummy/fabricated data)
    return (
        f"[Call Recording: {original_filename}]\n"
        f"Speaker 1 (Caller): [Recording attached: {original_filename}. Audio analysis could not isolate clear verbal dialogue. Please review the attached audio playback or enter your agreed deal terms manually.]"
    )
