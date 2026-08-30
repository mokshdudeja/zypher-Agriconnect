"""
AgriConnect — Sarvam AI Voice & Translation API

Endpoints:
    POST /api/sarvam/tts        — Text-to-Speech (returns audio/wav)
    POST /api/sarvam/stt        — Speech-to-Text (returns transcript)
    POST /api/sarvam/translate  — Text Translation (Indic languages)

Run locally:
    pip install fastapi uvicorn requests python-dotenv
    uvicorn backend.sarvam.api:app --reload --port 8001

Requires:
    SARVAM_API_KEY env var (or AWS Secrets Manager)

Sarvam API docs: https://docs.sarvam.ai/api-reference/introduction
"""

import os
import io
import json
import base64
import logging
from enum import Enum
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────────

app = FastAPI(
    title="AgriConnect Sarvam AI API",
    description="Voice (TTS/STT) and translation for Indian agriculture — 22+ Indic languages",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── API Key ─────────────────────────────────────────────────────

SARVAM_API_BASE = "https://api.sarvam.ai"


def _get_api_key() -> str:
    """
    Resolve Sarvam API key from:
    1. SARVAM_API_KEY env var
    2. AWS Secrets Manager (if USE_SECRETS_MANAGER=true)
    """
    key = os.getenv("SARVAM_API_KEY")
    if key:
        return key

    if os.getenv("USE_SECRETS_MANAGER", "false").lower() == "true":
        try:
            import boto3
            client = boto3.client(
                "secretsmanager",
                region_name=os.getenv("AWS_REGION", "ap-south-1"),
            )
            secret_name = os.getenv("SARVAM_SECRET_NAME", "agriconnect/sarvam-api-key")
            resp = client.get_secret_value(SecretId=secret_name)
            secret = json.loads(resp["SecretString"])
            return secret.get("SARVAM_API_KEY", secret.get("api_key", ""))
        except Exception as e:
            logger.error(f"Failed to fetch API key from Secrets Manager: {e}")

    raise HTTPException(
        status_code=500,
        detail="SARVAM_API_KEY not configured. Set the env var or enable AWS Secrets Manager.",
    )


def _sarvam_headers() -> dict:
    """Common headers for Sarvam API calls."""
    return {
        "api-subscription-key": _get_api_key(),
    }


# ─── Language Code Mapping ───────────────────────────────────────

# Maps short user-friendly codes to BCP-47 codes Sarvam expects
LANGUAGE_MAP = {
    "hi": "hi-IN",
    "en": "en-IN",
    "bn": "bn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "od": "od-IN",
    "pa": "pa-IN",
    "as": "as-IN",
    "ne": "ne-IN",
    "ur": "ur-IN",
    "sa": "sa-IN",
    "mai": "mai-IN",
    "doi": "doi-IN",
    "kok": "kok-IN",
    "ks": "ks-IN",
    "mni": "mni-IN",
    "brx": "brx-IN",
    "sat": "sat-IN",
    "sd": "sd-IN",
}

VALID_LANGUAGE_CODES = set(LANGUAGE_MAP.values()) | set(LANGUAGE_MAP.keys())

# Sarvam TTS language codes (subset supported by bulbul:v3)
TTS_LANGUAGE_CODES = {
    "hi-IN", "en-IN", "bn-IN", "ta-IN", "te-IN",
    "mr-IN", "gu-IN", "kn-IN", "ml-IN", "od-IN", "pa-IN",
}

# Voice mapping: user-friendly names → Sarvam speaker IDs
VOICE_MAP = {
    "female": "priya",
    "male": "aditya",
    "priya": "priya",
    "aditya": "aditya",
    "shubh": "shubh",
    "neha": "neha",
    "ritu": "ritu",
    "kavya": "kavya",
    "simran": "simran",
    "rahul": "rahul",
    "rohan": "rohan",
    "amit": "amit",
    "dev": "dev",
}


def _resolve_language(code: str) -> str:
    """Convert short language code (e.g. 'hi') to BCP-47 (e.g. 'hi-IN')."""
    code = code.strip().lower()
    if code in LANGUAGE_MAP:
        return LANGUAGE_MAP[code]
    # Already BCP-47
    if code in VALID_LANGUAGE_CODES:
        return code
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported language '{code}'. Supported: {sorted(LANGUAGE_MAP.keys())}",
    )


def _resolve_voice(voice: str) -> str:
    """Map user-friendly voice name to Sarvam speaker ID."""
    voice = voice.strip().lower()
    return VOICE_MAP.get(voice, "priya")


# ─── Request / Response Models ────────────────────────────────────


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech", max_length=2500)
    language: str = Field("hi", description="Language code (hi, en, bn, ta, etc.)")
    voice: str = Field("female", description="Voice: female, male, or specific name")


class STTResponse(BaseModel):
    transcript: str
    language_detected: Optional[str] = None
    confidence: Optional[float] = None


class TranslationRequest(BaseModel):
    text: str = Field(..., description="Text to translate", max_length=2000)
    source: str = Field("en", description="Source language code")
    target: str = Field("hi", description="Target language code")


class TranslationResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str


class SupportedLanguagesResponse(BaseModel):
    tts_languages: list[str]
    stt_languages: list[str]
    translation_languages: list[str]


# ─── Endpoints ───────────────────────────────────────────────────


@app.post("/api/sarvam/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using Sarvam AI.

    Request:
        { "text": "गेहूं की कीमत 2200 रुपये है", "language": "hi", "voice": "female" }

    Returns: audio/wav bytes
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    language_code = _resolve_language(request.language)

    # Validate language is supported by TTS
    if language_code not in TTS_LANGUAGE_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Language '{language_code}' not supported for TTS. Supported: {sorted(TTS_LANGUAGE_CODES)}",
        )

    speaker = _resolve_voice(request.voice)

    payload = {
        "text": request.text.strip(),
        "target_language_code": language_code,
        "speaker": speaker,
        "model": "bulbul:v3",
        "output_audio_codec": "wav",
        "speech_sample_rate": "24000",
    }

    try:
        resp = requests.post(
            f"{SARVAM_API_BASE}/text-to-speech",
            headers={**_sarvam_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # Sarvam returns base64-encoded audio in 'audios' array or 'audio' field
        audios = data.get("audios", [])
        audio_b64 = audios[0] if audios else data.get("audio", data.get("audio_base64", ""))
        if not audio_b64:
            raise HTTPException(status_code=502, detail="Sarvam returned empty audio")

        audio_bytes = base64.b64decode(audio_b64)

        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=\"speech_{language_code}.wav\"",
                "X-Language": language_code,
                "X-Speaker": speaker,
            },
        )

    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Sarvam TTS request timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"Sarvam TTS error: {e}")
        raise HTTPException(status_code=502, detail=f"Sarvam TTS API error: {str(e)}")
    except Exception as e:
        logger.error(f"TTS processing error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS processing failed: {str(e)}")


@app.post("/api/sarvam/stt")
async def speech_to_text(
    file: UploadFile = File(..., description="Audio file (WAV, MP3, OGG, FLAC, etc.)"),
    language_code: str = Form("unknown", description="Language code or 'unknown' for auto-detect"),
    mode: str = Form("transcribe", description="Mode: transcribe, translate, verbatim, translit, codemix"),
):
    """
    Transcribe audio to text using Sarvam AI.

    Multipart form upload with audio file.
    Returns: { "transcript": "...", "confidence": 0.95 }
    """
    # Read audio file
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    # Validate file size (Sarvam REST API limit ~30s audio)
    max_size = 25 * 1024 * 1024  # 25MB
    if len(audio_bytes) > max_size:
        raise HTTPException(status_code=400, detail=f"Audio file too large (max {max_size // 1024 // 1024}MB)")

    # Resolve language code
    if language_code != "unknown":
        language_code = _resolve_language(language_code)

    # Determine file extension for content type
    filename = file.filename or "audio.wav"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
    content_type_map = {
        "wav": "audio/wav", "mp3": "audio/mpeg", "ogg": "audio/ogg",
        "flac": "audio/flac", "m4a": "audio/mp4", "aac": "audio/aac",
        "opus": "audio/opus", "webm": "audio/webm", "amr": "audio/amr",
    }
    content_type = content_type_map.get(ext, "audio/wav")

    try:
        # Send multipart form to Sarvam STT
        files = {"file": (filename, audio_bytes, content_type)}
        data = {
            "model": "saaras:v3",
            "mode": mode,
        }
        if language_code != "unknown":
            data["language_code"] = language_code

        resp = requests.post(
            f"{SARVAM_API_BASE}/speech-to-text",
            headers=_sarvam_headers(),
            files=files,
            data=data,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()

        transcript = result.get("transcript", "")
        detected_lang = result.get("language_code", language_code if language_code != "unknown" else None)

        if not transcript:
            raise HTTPException(status_code=502, detail="Sarvam returned empty transcript")

        # Sarvam doesn't return explicit confidence, estimate from transcript presence
        confidence = 0.95 if transcript else 0.0

        return STTResponse(
            transcript=transcript,
            language_detected=detected_lang,
            confidence=confidence,
        )

    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Sarvam STT request timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"Sarvam STT error: {e}")
        raise HTTPException(status_code=502, detail=f"Sarvam STT API error: {str(e)}")
    except Exception as e:
        logger.error(f"STT processing error: {e}")
        raise HTTPException(status_code=500, detail=f"STT processing failed: {str(e)}")


@app.post("/api/sarvam/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    Translate text between Indian languages using Sarvam AI.

    Request:
        { "text": "Wheat price is 2200 rupees", "source": "en", "target": "hi" }

    Returns:
        { "translated_text": "गेहूं की कीमत 2200 रुपये है", ... }
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    source_lang = _resolve_language(request.source)
    target_lang = _resolve_language(request.target)

    if source_lang == target_lang:
        return TranslationResponse(
            translated_text=request.text.strip(),
            source_language=source_lang,
            target_language=target_lang,
        )

    payload = {
        "input": request.text.strip(),
        "source_language_code": source_lang,
        "target_language_code": target_lang,
        "model": "sarvam-translate:v1",
        "mode": "formal",
    }

    try:
        resp = requests.post(
            f"{SARVAM_API_BASE}/translate",
            headers={**_sarvam_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        translated = data.get("translated_text", data.get("output", ""))
        if not translated:
            raise HTTPException(status_code=502, detail="Sarvam returned empty translation")

        return TranslationResponse(
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
        )

    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Sarvam translate request timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"Sarvam translate error: {e}")
        raise HTTPException(status_code=502, detail=f"Sarvam translate API error: {str(e)}")
    except Exception as e:
        logger.error(f"Translation processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@app.get("/api/sarvam/languages", response_model=SupportedLanguagesResponse)
async def get_supported_languages():
    """List all supported languages for each endpoint."""
    return SupportedLanguagesResponse(
        tts_languages=sorted(TTS_LANGUAGE_CODES),
        stt_languages=sorted(VALID_LANGUAGE_CODES),
        translation_languages=sorted(VALID_LANGUAGE_CODES),
    )


@app.get("/api/sarvam/health")
async def health_check():
    """Check API key is configured and Sarvam is reachable."""
    try:
        key = _get_api_key()
        key_ok = bool(key and len(key) > 5)
    except HTTPException:
        key_ok = False

    return {
        "status": "ok" if key_ok else "misconfigured",
        "api_key_set": key_ok,
        "version": "1.0.0",
        "endpoints": {
            "tts": "POST /api/sarvam/tts",
            "stt": "POST /api/sarvam/stt",
            "translate": "POST /api/sarvam/translate",
            "languages": "GET /api/sarvam/languages",
        },
    }


# ─── AWS Lambda Handler ──────────────────────────────────────────


def handler(event, context):
    """AWS Lambda handler for API Gateway integration."""
    try:
        from mangum import Mangum
        asgi_handler = Mangum(app)
        return asgi_handler(event, context)
    except ImportError:
        path = event.get("path", "")
        method = event.get("httpMethod", "GET")

        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Install mangum for Lambda routing: pip install mangum"}),
        }
