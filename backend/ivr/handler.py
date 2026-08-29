"""
AgriConnect — IVR Call Flow Handler for Farmers

Voice-based crop price inquiry system using Exotel telephony + Sarvam AI.

Call flow:
    1. Farmer calls → POST /api/ivr/incoming
       → Welcome message in Hindi via Sarvam TTS
       → Gather speech: "कृपया फसल का नाम बताएं"

    2. Exotel sends transcribed speech → POST /api/ivr/gather
       → Parse crop name from SpeechResult (Hindi/English keyword matching)
       → Fetch price from prediction API
       → Generate Sarvam TTS audio with price info
       → Return Exotel XML with <Play> audio or <Say> fallback

    3. Call logged to DynamoDB (90-day TTL)

Exotel webhook docs: https://docs.exotel.com/elves/webhook/
Sarvam AI: https://docs.sarvam.ai/api-reference/introduction

Run locally:
    pip install fastapi uvicorn requests boto3 python-dotenv
    uvicorn backend.ivr.handler:app --reload --port 8002

Requires:
    EXOTEL_SID, EXOTEL_API_KEY, EXOTEL_ACCOUNT_SID
    SARVAM_API_KEY
    API_BASE_URL (your deployed prediction API base, e.g. https://api.agriconnect.in)
"""

import os
import re
import json
import time
import base64
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from xml.sax.saxutils import escape as xml_escape

import requests
from fastapi import FastAPI, HTTPException, Request, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, PlainTextResponse

logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────────

app = FastAPI(
    title="AgriConnect IVR — Farmer Voice API",
    description="Voice-based crop price inquiry for Indian farmers via Exotel + Sarvam AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the prediction app for /api/predict, /api/weather, /api/crop-recommend routes
try:
    from prediction.api.app import app as prediction_app
    # prediction routes already have /api prefix, mount at root
    for route in prediction_app.routes:
        if hasattr(route, 'path') and not route.path.startswith('/api/ivr'):
            app.routes.append(route)
except ImportError:
    logger.warning("Could not import prediction API app")

# Mount the Sarvam API for /api/sarvam/tts, /api/sarvam/stt, /api/sarvam/translate routes
try:
    from sarvam.api import app as sarvam_app
    for route in sarvam_app.routes:
        if hasattr(route, 'path') and not route.path.startswith('/api/ivr'):
            app.routes.append(route)
except ImportError:
    logger.warning("Could not import Sarvam API app")

# Mount the Farmer Phone Platform for /api/ivr/incoming, /api/ivr/menu, etc.
try:
    from ivr.farmer_phone import app as phone_app
    for route in phone_app.routes:
        if hasattr(route, 'path'):
            # Skip routes that already exist in the main app
            existing = [r.path for r in app.routes if hasattr(r, 'path')]
            if route.path not in existing:
                app.routes.append(route)
except ImportError:
    logger.warning("Could not import Farmer Phone Platform")

# Mount Voice Agents for /api/voice-agents/* routes
try:
    from voice_agents import app as va_app
    for route in va_app.routes:
        if hasattr(route, 'path'):
            existing = [r.path for r in app.routes if hasattr(r, 'path')]
            if route.path not in existing:
                app.routes.append(route)
except ImportError:
    logger.warning("Could not import Voice Agents module")


# ─── Config ──────────────────────────────────────────────────────

EXOTEL_SID = os.getenv("EXOTEL_SID", "")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY", "")
EXOTEL_ACCOUNT_SID = os.getenv("EXOTEL_ACCOUNT_SID", "")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_API_BASE = "https://api.sarvam.ai"

# Base URL for calling the prediction API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Default state if caller's state cannot be determined
DEFAULT_STATE = os.getenv("DEFAULT_STATE", "uttar_pradesh")

# DynamoDB
USE_DYNAMODB = os.getenv("USE_DYNAMODB", "false").lower() == "true"
CALL_LOG_TABLE = os.getenv("DYNAMODB_CALL_LOG_TABLE", "agriconnect-ivr-calls")
CALL_LOG_TTL_DAYS = 90


# ─── Supported Crops ─────────────────────────────────────────────

SUPPORTED_CROPS = [
    "wheat", "rice", "maize", "cotton", "soybean",
    "potato", "tomato", "onion", "groundnut", "sugarcane",
]

SUPPORTED_STATES = [
    "uttar_pradesh", "maharashtra", "madhya_pradesh", "west_bengal",
    "rajasthan", "karnataka", "andhra_pradesh", "gujarat",
    "punjab", "tamil_nadu", "haryana", "bihar",
]

# ─── Hindi ↔ English Crop Keyword Mapping ────────────────────────
# Maps Hindi/English voice inputs to canonical crop names
CROP_KEYWORDS = {
    # Hindi names (Devanagari)
    "गेहूं": "wheat", "गेहूँ": "wheat", "gehun": "wheat", "gehu": "wheat",
    "चावल": "rice", "चावळ": "rice", "धान": "rice", "dhaan": "rice",
    "मक्का": "maize", "मकई": "maize", "makka": "maize", "makai": "maize",
    "कपास": "cotton", "कपाह": "cotton", "kapas": "cotton",
    "सोयाबीन": "soybean", "सोयाबिन": "soybean", "soyabean": "soybean",
    "आलू": "potato", "aalu": "potato", "aloo": "potato",
    "टमाटर": "tomato", "tamatar": "tomato",
    "प्याज": "onion", "प्याज़": "onion", "pyaaz": "onion", "pyaj": "onion",
    "मूंगफली": "groundnut", "मूंगफल": "groundnut", "moongfali": "groundnut",
    "गन्ना": "sugarcane", "ganna": "sugarcane", "gur": "sugarcane",
    # English names
    "wheat": "wheat",
    "rice": "rice", "paddy": "rice", "dhan": "rice",
    "maize": "maize", "corn": "maize", "makka": "maize",
    "cotton": "cotton", "kapas": "cotton",
    "soybean": "soybean", "soya": "soybean",
    "potato": "potato", "aloo": "potato",
    "tomato": "tomato",
    "onion": "onion",
    "groundnut": "groundnut", "peanut": "groundnut", "moongfali": "groundnut",
    "sugarcane": "sugarcane", "gur": "sugarcane",
}

# ─── Hindi State Mapping ─────────────────────────────────────────

STATE_KEYWORDS = {
    "उत्तर प्रदेश": "uttar_pradesh", "up": "uttar_pradesh", "यूपी": "uttar_pradesh",
    "महाराष्ट्र": "maharashtra", "महाराष्ट": "maharashtra",
    "मध्य प्रदेश": "madhya_pradesh", "mp": "madhya_pradesh", "एमपी": "madhya_pradesh",
    "पश्चिम बंगाल": "west_bengal", "bengal": "west_bengal",
    "राजस्थान": "rajasthan",
    "कर्नाटक": "karnataka", "karnataka": "karnataka",
    "आंध्र प्रदेश": "andhra_pradesh", "ap": "andhra_pradesh",
    "गुजरात": "gujarat",
    "पंजाब": "punjab",
    "तमिल नाडु": "tamil_nadu", "tamil": "tamil_nadu",
    "हरियाणा": "haryana",
    "बिहार": "bihar",
}


# ─── Exotel XML Helpers ──────────────────────────────────────────

def twiml_say(text: str, language: str = "hi-IN", voice: str = "female") -> str:
    """Generate Exotel TwiML <Say> verb."""
    return f'<Say language="{language}" voice="{voice}">{xml_escape(text)}</Say>'


def twiml_play(audio_url: str) -> str:
    """Generate Exotel TwiML <Play> verb for pre-generated audio."""
    return f"<Play>{xml_escape(audio_url)}</Play>"


def twiml_gather(action_url: str, text: str, speech_timeout: int = 3,
                  language: str = "hi-IN", num_digits: int = 0) -> str:
    """
    Generate Exotel TwiML <Gather> verb with speech recognition.
    Exotel uses its own STT for Gather — no need for Sarvam STT here.
    """
    return (
        f'<Gather input="speech" action="{xml_escape(action_url)}" '
        f'method="POST" speechTimeout="{speech_timeout}" '
        f'language="{language}">'
        f'{twiml_say(text, language)}'
        f"</Gather>"
    )


def twiml_response(verbs: list[str]) -> str:
    """Wrap TwiML verbs in Response envelope."""
    body = "\n".join(verbs)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n{body}\n</Response>'


def twiml_hangup() -> str:
    return "<Hangup/>"


def twiml_redirect(url: str) -> str:
    return f'<Redirect method="POST">{xml_escape(url)}</Redirect>'


# ─── Sarvam TTS ──────────────────────────────────────────────────

def sarvam_tts(text: str, language: str = "hi-IN", speaker: str = "priya") -> Optional[bytes]:
    """
    Call Sarvam TTS API to generate audio.
    Returns WAV bytes or None on failure.
    """
    if not SARVAM_API_KEY:
        logger.warning("SARVAM_API_KEY not set, cannot generate TTS audio")
        return None

    payload = {
        "text": text,
        "language_code": language,
        "speaker": speaker,
        "model": "bulbul:v3",
    }

    try:
        resp = requests.post(
            f"{SARVAM_API_BASE}/text-to-speech",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        if resp.status_code != 200:
            logger.error(f"Sarvam TTS {resp.status_code}: {resp.text[:500]}")
            logger.error(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
            return None
        data = resp.json()

        # Sarvam v3 returns audios array of base64 strings
        audios = data.get("audios", [])
        if not audios:
            audio_b64 = data.get("audio", data.get("audio_base64", ""))
            if audio_b64:
                audios = [audio_b64]
        
        if not audios:
            logger.error("Sarvam TTS returned empty audio")
            return None

        combined = "".join(audios)
        return base64.b64decode(combined)

    except requests.exceptions.HTTPError as e:
        logger.error(f"Sarvam TTS HTTP {e.response.status_code}: {e.response.text[:500]}")
        logger.error(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
        return None
    except Exception as e:
        logger.error(f"Sarvam TTS failed: {e}")
        return None


# ─── Crop Name Parsing ───────────────────────────────────────────

def parse_crop_name(transcript: str) -> Optional[str]:
    """
    Extract crop name from speech transcript using keyword matching.
    Handles Hindi (Devanagari), Romanized Hindi, and English.
    """
    if not transcript:
        return None

    text = transcript.lower().strip()

    # Direct match first
    for keyword, crop in CROP_KEYWORDS.items():
        if keyword.lower() in text:
            return crop

    # Fuzzy: remove common filler words and try again
    fillers = [
        "मुझे", "बताओ", "बताइए", "की", "का", "के", "है", "हैं",
        "price", "rate", "tell", "me", "what", "is", "the", "of",
        "मैं", "जानना", "चाहता", "हूँ", "चाहता", "जानना", "चाहूँ",
        "please", "batao", "bataiye", "kya", "hai", "ka", "ki", "ke",
    ]
    cleaned = text
    for filler in fillers:
        cleaned = cleaned.replace(filler, "")
    cleaned = cleaned.strip()

    for keyword, crop in CROP_KEYWORDS.items():
        if keyword.lower() in cleaned:
            return crop

    # Last resort: check if any crop name is a substring
    for keyword, crop in CROP_KEYWORDS.items():
        if crop in text:
            return crop

    return None


def parse_state_name(transcript: str) -> Optional[str]:
    """Extract state name from speech transcript."""
    if not transcript:
        return None

    text = transcript.lower().strip()

    for keyword, state in STATE_KEYWORDS.items():
        if keyword.lower() in text:
            return state

    return None


# ─── Price Fetching ──────────────────────────────────────────────

def fetch_crop_price(crop: str, state: str) -> Optional[dict]:
    """Call the prediction API to get current crop price."""
    try:
        url = f"{API_BASE_URL}/api/predict/{crop}/{state}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Price fetch failed for {crop}/{state}: {e}")
        return None


# ─── Response Generation ─────────────────────────────────────────

def generate_price_response_text(crop: str, state: str, prediction: dict) -> str:
    """
    Generate natural Hindi response text for crop price info.
    This is used for both <Say> (Exotel TTS) and <Play> (Sarvam TTS).
    """
    crop_hindi = {
        "wheat": "गेहूं", "rice": "चावल", "maize": "मक्का",
        "cotton": "कपास", "soybean": "सोयाबीन", "potato": "आलू",
        "tomato": "टमाटर", "onion": "प्याज", "groundnut": "मूंगफली",
        "sugarcane": "गन्ना",
    }

    state_hindi = {
        "uttar_pradesh": "उत्तर प्रदेश", "maharashtra": "महाराष्ट्र",
        "madhya_pradesh": "मध्य प्रदेश", "west_bengal": "पश्चिम बंगाल",
        "rajasthan": "राजस्थान", "karnataka": "कर्नाटक",
        "andhra_pradesh": "आंध्र प्रदेश", "gujarat": "गुजरात",
        "punjab": "पंजाब", "tamil_nadu": "तमिल नाडु",
        "haryana": "हरियाणा", "bihar": "बिहार",
    }

    crop_hi = crop_hindi.get(crop, crop)
    state_hi = state_hindi.get(state, state)

    current = int(prediction.get("current_price", 0))
    predicted = int(prediction.get("predicted_price_7d", 0))
    trend = prediction.get("trend", "stable")

    trend_hindi = {
        "bullish": "बढ़ रही है",
        "bearish": "गिर रही है",
        "stable": "स्थिर है",
    }
    trend_text = trend_hindi.get(trend, "स्थिर है")

    # Build natural sentence
    response = (
        f"{state_hi} में {crop_hi} की मौजूदा कीमत "
        f"{current} रुपये प्रति क्विंटल है। "
    )

    if trend == "bullish":
        response += (
            f"अगले 7 दिन में कीमत {predicted} रुपये तक बढ़ सकती है। "
            f"बिक्री का सबसे अच्छा समय अगले 7 दिन है।"
        )
    elif trend == "bearish":
        response += (
            f"अगले 7 दिन में कीमत {predicted} रुपये तक गिर सकती है। "
            f"अगर बेचना है तो जल्दी बेचें।"
        )
    else:
        response += (
            f"कीमतें अगले 7 दिन स्थिर रहेंगी, "
            f"लगभग {predicted} रुपये प्रति क्विंटल।"
        )

    return response


# ─── DynamoDB Call Logging ────────────────────────────────────────

_dynamodb = None
_call_log_table = None


def _get_call_log_table():
    """Lazy-init DynamoDB call log table."""
    global _dynamodb, _call_log_table
    if _call_log_table is None:
        try:
            import boto3
            _dynamodb = boto3.resource(
                "dynamodb",
                region_name=os.getenv("AWS_REGION", "ap-south-1"),
            )
            _call_log_table = _dynamodb.Table(CALL_LOG_TABLE)
        except Exception as e:
            logger.warning(f"DynamoDB init failed: {e}. Using in-memory log.")
    return _call_log_table


# In-memory fallback for local dev
_call_log_memory = []


def log_call(call_id: str, phone_number: str, crop_queried: str,
             state: str, duration_seconds: int = 0, status: str = "completed",
             transcript: str = "", error: str = ""):
    """Log an IVR call to DynamoDB (or in-memory fallback)."""
    now = datetime.now()
    ttl_timestamp = int(now.timestamp()) + (CALL_LOG_TTL_DAYS * 86400)

    record = {
        "call_id": call_id,
        "phone_number": phone_number,
        "crop_queried": crop_queried,
        "state": state,
        "duration_seconds": duration_seconds,
        "status": status,
        "transcript": transcript,
        "error": error,
        "timestamp": now.isoformat(),
        "ttl": ttl_timestamp,
    }

    if USE_DYNAMODB:
        table = _get_call_log_table()
        if table:
            try:
                table.put_item(Item=record)
                logger.info(f"Logged call {call_id} to DynamoDB")
                return
            except Exception as e:
                logger.warning(f"DynamoDB write failed: {e}. Falling back to memory.")

    # In-memory fallback
    _call_log_memory.append(record)
    if len(_call_log_memory) > 1000:
        _call_log_memory.pop(0)
    logger.info(f"Logged call {call_id} to memory ({len(_call_log_memory)} calls)")


def get_call_stats(phone_number: Optional[str] = None) -> dict:
    """Get call statistics."""
    if USE_DYNAMODB and _get_call_log_table():
        try:
            import boto3
            table = _get_call_log_table()
            resp = table.scan()
            items = resp.get("Items", [])
        except Exception:
            items = _call_log_memory
    else:
        items = _call_log_memory

    if phone_number:
        items = [i for i in items if i.get("phone_number") == phone_number]

    total = len(items)
    by_crop = {}
    by_status = {}
    for item in items:
        crop = item.get("crop_queried", "unknown")
        by_crop[crop] = by_crop.get(crop, 0) + 1
        status = item.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "total_calls": total,
        "by_crop": by_crop,
        "by_status": by_status,
    }


# ─── Phone → State Detection ─────────────────────────────────────

# Indian telecom circle to state mapping (simplified)
PHONE_STATE_MAP = {
    # UP & Uttarakhand
    "59": "uttar_pradesh", "60": "uttar_pradesh", "61": "uttar_pradesh",
    "62": "uttar_pradesh", "63": "uttar_pradesh", "64": "uttar_pradesh",
    "65": "uttar_pradesh", "66": "uttar_pradesh", "67": "uttar_pradesh",
    "68": "uttar_pradesh", "69": "uttar_pradesh", "70": "uttar_pradesh",
    # Maharashtra
    "71": "maharashtra", "72": "maharashtra", "73": "maharashtra",
    "74": "maharashtra", "75": "maharashtra", "76": "maharashtra",
    # MP
    "77": "madhya_pradesh", "78": "madhya_pradesh", "79": "madhya_pradesh",
    "80": "madhya_pradesh", "81": "madhya_pradesh",
    # Gujarat
    "82": "gujarat", "83": "gujarat", "84": "gujarat",
    # Rajasthan
    "85": "rajasthan", "86": "rajasthan", "87": "rajasthan",
    # Punjab & Haryana
    "88": "punjab", "89": "punjab",
    # Bihar & Jharkhand
    "90": "bihar", "91": "bihar",
    # West Bengal
    "92": "west_bengal", "93": "west_bengal",
    # Karnataka
    "94": "karnataka", "95": "karnataka",
    # Tamil Nadu
    "96": "tamil_nadu", "97": "tamil_nadu",
    # Andhra Pradesh & Telangana
    "98": "andhra_pradesh", "99": "andhra_pradesh",
}


def detect_state_from_phone(phone: str) -> str:
    """Best-effort state detection from phone number prefix."""
    # Strip country code and leading zeros
    clean = re.sub(r"^(\+91|91|0)", "", phone.strip())
    if len(clean) >= 4:
        prefix = clean[:2]
        return PHONE_STATE_MAP.get(prefix, DEFAULT_STATE)
    return DEFAULT_STATE


# ─── Endpoints ───────────────────────────────────────────────────


@app.post("/api/ivr/incoming")
async def ivr_incoming(request: Request):
    """
    Exotel incoming call webhook.

    Exotel sends: CallSid, From, To, Direction, CallStatus, etc.
    We respond with TwiML: welcome message + gather speech.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    caller = form.get("From", "unknown")
    direction = form.get("Direction", "inbound")

    logger.info(f"Incoming call: sid={call_sid}, from={caller}, direction={direction}")

    # Detect state from phone number
    detected_state = detect_state_from_phone(caller)
    logger.info(f"Detected state: {detected_state} from phone: {caller}")

    # Store call context in session (Exotel passes this back in callbacks)
    # We encode state in the action URL query params instead
    welcome_text = (
        "नमस्ते! आपने कृषि सेवा को कॉल किया है। "
        "कृपया फसल का नाम बताएं। "
        "जैसे गेहूं, चावल, मक्का, या प्याज।"
    )

    # Build gather action URL with state context
    base = os.getenv("PUBLIC_API_BASE", "http://localhost:8002")
    gather_action = f"{base}/api/ivr/gather?state={detected_state}"

    xml = twiml_response([
        twiml_gather(
            action_url=gather_action,
            text=welcome_text,
            speech_timeout=3,
            language="hi-IN",
        ),
        # Fallback if no speech detected
        twiml_say("आपने कुछ नहीं बोला। कृपया दोबारा कॉल करें।"),
        twiml_hangup(),
    ])

    log_call(
        call_id=call_sid,
        phone_number=caller,
        crop_queried="",
        state=detected_state,
        status="incoming",
    )

    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/gather")
async def ivr_gather(request: Request):
    """
    Exotel gather speech callback.

    Exotel sends: CallSid, From, SpeechResult, Confidence
    We parse crop name, fetch price, respond with TTS audio.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    caller = form.get("From", "unknown")
    speech_result = form.get("SpeechResult", "")
    confidence = form.get("Confidence", "0")
    state = request.query_params.get("state", DEFAULT_STATE)

    logger.info(
        f"Gather callback: sid={call_sid}, speech='{speech_result}', "
        f"confidence={confidence}, state={state}"
    )

    # Parse crop name from speech
    crop = parse_crop_name(speech_result)

    if not crop:
        # Ask again with a hint
        retry_text = (
            f"मुझे '{speech_result}' समझ नहीं आया। "
            "कृपया फसल का नाम दोबारा बताएं। "
            "जैसे गेहूं, चावल, मक्का, कपास, आलू, टमाटर, प्याज, "
            "सोयाबीन, मूंगफली, या गन्ना।"
        )

        base = os.getenv("PUBLIC_API_BASE", "http://localhost:8002")
        gather_action = f"{base}/api/ivr/gather?state={state}"

        xml = twiml_response([
            twiml_gather(
                action_url=gather_action,
                text=retry_text,
                speech_timeout=4,
                language="hi-IN",
            ),
            twiml_say("कोई जवाब नहीं मिला। कृपया दोबारा कॉल करें।"),
            twiml_hangup(),
        ])

        log_call(
            call_id=call_sid,
            phone_number=caller,
            crop_queried="unrecognized",
            state=state,
            status="unrecognized_crop",
            transcript=speech_result,
        )

        return Response(content=xml, media_type="application/xml")

    # Also check if caller mentioned a state in their speech
    detected_state = parse_state_name(speech_result) or state

    # Fetch price from prediction API
    prediction = fetch_crop_price(crop, detected_state)

    if not prediction:
        error_text = (
            f"माफ़ कीजिए, {crop} की कीमत की जानकारी अभी उपलब्ध नहीं है। "
            "कृपया बाद में दोबारा कॉल करें।"
        )

        xml = twiml_response([
            twiml_say(error_text),
            twiml_hangup(),
        ])

        log_call(
            call_id=call_sid,
            phone_number=caller,
            crop_queried=crop,
            state=detected_state,
            status="price_unavailable",
            transcript=speech_result,
        )

        return Response(content=xml, media_type="application/xml")

    # Generate response text
    response_text = generate_price_response_text(crop, detected_state, prediction)

    # Try to get Sarvam TTS audio for better quality
    audio_bytes = sarvam_tts(response_text, language="hi-IN", speaker="priya")

    base = os.getenv("PUBLIC_API_BASE", "http://localhost:8002")

    if audio_bytes:
        # Store audio temporarily and return <Play> verb
        # In production, upload to S3 and use the URL
        audio_url = f"{base}/api/ivr/audio/{call_sid}"
        # Store audio in memory cache for retrieval
        _audio_cache[call_sid] = audio_bytes

        xml = twiml_response([
            twiml_play(audio_url),
            twiml_hangup(),
        ])
    else:
        # Fallback to Exotel's built-in TTS via <Say>
        xml = twiml_response([
            twiml_say(response_text, language="hi-IN"),
            twiml_hangup(),
        ])

    log_call(
        call_id=call_sid,
        phone_number=caller,
        crop_queried=crop,
        state=detected_state,
        status="completed",
        transcript=speech_result,
    )

    return Response(content=xml, media_type="application/xml")


# ─── Audio Cache (for <Play> serving) ───────────────────────────

_audio_cache = {}


@app.get("/api/ivr/audio/{call_sid}")
async def serve_ivr_audio(call_sid: str):
    """Serve cached TTS audio for a call. Used by Exotel <Play>."""
    audio = _audio_cache.get(call_sid)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found or expired")

    # Clean up after serving
    _audio_cache.pop(call_sid, None)

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Content-Disposition": f"attachment; filename=\"ivr_{call_sid}.wav\""},
    )


@app.post("/api/sarvam/tts")
async def sarvam_tts_endpoint(request: Request):
    """
    Sarvam TTS endpoint for the frontend Voice Agent.
    Returns audio/wav.
    """
    body = await request.json()
    text = body.get("text", "")
    language = body.get("language", "hi")
    voice = body.get("voice", "priya")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # Resolve language code
    lang_map = {'hi': 'hi-IN', 'en': 'en-IN', 'ta': 'ta-IN', 'te': 'te-IN', 'kn': 'kn-IN', 'mr': 'mr-IN'}
    lang_code = lang_map.get(language, language if '-' in language else f"{language}-IN")

    audio = sarvam_tts(text, language=lang_code, speaker=voice)
    if not audio:
        raise HTTPException(status_code=502, detail="TTS generation failed")

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=\"tts.wav\""},
    )


@app.post("/api/sarvam/translate")
async def sarvam_translate_endpoint(request: Request):
    """
    Sarvam Translate endpoint for the frontend.
    """
    body = await request.json()
    text = body.get("text", "")
    source = body.get("source", "en")
    target = body.get("target", "hi")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        headers = {"API-Subscription-Key": SARVAM_API_KEY, "Content-Type": "application/json"}
        payload = {
            "input": text,
            "source_language_code": source if '-' in source else f"{source}-IN",
            "target_language_code": target if '-' in target else f"{target}-IN",
            "mode": "formal"
        }
        resp = requests.post(f"{SARVAM_API_BASE}/translate", json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        return {"translated_text": result.get("translated_text", text), "source": source, "target": target}
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=502, detail="Translation failed")


@app.post("/api/ivr/tts")
async def ivr_tts_preview(request: Request):
    """
    Preview endpoint: generate TTS audio for any text.
    Useful for testing without making a real call.
    """
    body = await request.json()
    text = body.get("text", "")
    language = body.get("language", "hi-IN")
    speaker = body.get("speaker", "priya")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    audio = sarvam_tts(text, language=language, speaker=speaker)
    if not audio:
        raise HTTPException(status_code=502, detail="TTS generation failed")

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=\"tts_preview.wav\""},
    )


@app.post("/api/ivr/test-crop")
async def test_crop_lookup(request: Request):
    """
    Test endpoint: look up crop price without a phone call.
    Useful for debugging and development.
    """
    body = await request.json()
    crop = body.get("crop", "")
    state = body.get("state", DEFAULT_STATE)

    if not crop:
        raise HTTPException(status_code=400, detail="crop is required")

    # Normalize
    matched_crop = parse_crop_name(crop) or crop.lower().strip()

    if matched_crop not in SUPPORTED_CROPS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported crop '{matched_crop}'. Supported: {SUPPORTED_CROPS}",
        )

    if state not in SUPPORTED_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported state '{state}'. Supported: {SUPPORTED_STATES}",
        )

    prediction = fetch_crop_price(matched_crop, state)
    if not prediction:
        raise HTTPException(status_code=502, detail="Price fetch failed")

    response_text = generate_price_response_text(matched_crop, state, prediction)

    return {
        "crop": matched_crop,
        "state": state,
        "prediction": prediction,
        "response_text_hindi": response_text,
    }


@app.get("/api/ivr/stats")
async def ivr_stats(phone: Optional[str] = Query(None)):
    """Get IVR call statistics."""
    return get_call_stats(phone)


@app.get("/api/ivr/crops")
async def ivr_crops():
    """List supported crops with Hindi names."""
    hindi = {
        "wheat": "गेहूं", "rice": "चावल", "maize": "मक्का",
        "cotton": "कपास", "soybean": "सोयाबीन", "potato": "आलू",
        "tomato": "टमाटर", "onion": "प्याज", "groundnut": "मूंगफली",
        "sugarcane": "गन्ना",
    }
    return {
        "crops": [
            {"name": c, "hindi": hindi.get(c, c), "voice_keywords": [
                k for k, v in CROP_KEYWORDS.items() if v == c
            ]}
            for c in SUPPORTED_CROPS
        ]
    }


@app.get("/api/ivr/health")
async def ivr_health():
    """IVR system health check."""
    return {
        "status": "ok",
        "exotel_configured": bool(EXOTEL_SID and EXOTEL_API_KEY),
        "sarvam_configured": bool(SARVAM_API_KEY),
        "dynamodb": USE_DYNAMODB,
        "api_base": API_BASE_URL,
        "version": "1.0.0",
    }


# ─── Exotel Outbound Call (optional) ─────────────────────────────

@app.post("/api/ivr/call")
async def initiate_outbound_call(request: Request):
    """
    Initiate an outbound IVR call to a farmer.
    Useful for proactive price alerts.
    """
    body = await request.json()
    phone = body.get("phone", "")
    crop = body.get("crop", "")
    state = body.get("state", DEFAULT_STATE)

    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")
    if not EXOTEL_SID or not EXOTEL_API_KEY:
        raise HTTPException(status_code=503, detail="Exotel not configured")

    # Initiate call via Exotel API
    try:
        base = os.getenv("PUBLIC_API_BASE", "http://localhost:8002")
        callback_url = f"{base}/api/ivr/incoming"

        resp = requests.post(
            f"https://api.exotel.com/v1/Accounts/{EXOTEL_SID}/Calls.json",
            auth=(EXOTEL_SID, EXOTEL_API_KEY),
            data={
                "From": phone,
                "To": os.getenv("EXOTEL_VIRTUAL_NUMBER", ""),
                "CallerId": os.getenv("EXOTEL_VIRTUAL_NUMBER", ""),
                "Url": callback_url,
                "StatusCallback": f"{base}/api/ivr/status",
                "StatusCallbackMethod": "POST",
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()

        return {
            "status": "initiated",
            "call_sid": result.get("Call", {}).get("Sid", ""),
            "phone": phone,
        }

    except Exception as e:
        logger.error(f"Outbound call failed: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to initiate call: {str(e)}")


@app.post("/api/ivr/status")
async def ivr_status_callback(request: Request):
    """Exotel call status callback. Logs final call status."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    status = form.get("CallStatus", "unknown")
    duration = form.get("CallDuration", "0")

    logger.info(f"Call status: sid={call_sid}, status={status}, duration={duration}s")

    log_call(
        call_id=call_sid,
        phone_number=form.get("From", ""),
        crop_queried="",
        state="",
        duration_seconds=int(duration) if duration.isdigit() else 0,
        status=f"call_{status}",
    )

    return PlainTextResponse("OK")


# ─── AWS Lambda Handler ──────────────────────────────────────────


def handler(event, context):
    """AWS Lambda handler for API Gateway integration."""
    try:
        from mangum import Mangum
        asgi_handler = Mangum(app)
        return asgi_handler(event, context)
    except ImportError:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Install mangum for Lambda: pip install mangum"}),
        }
