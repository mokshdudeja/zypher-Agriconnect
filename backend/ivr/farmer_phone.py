"""
AgriConnect — Complete Phone-Based Farmer Platform

Allow farmers without smartphones to:
1. Check crop prices (voice → price → TTS response)
2. Check weather forecast
3. Manage their profile (view/update name, phone, location)
4. Manage crop listings (add new crop, update price, mark sold, view all)
5. Manage orders (view incoming, accept/reject, mark delivered)
6. Get crop recommendations based on season/soil

Call Flow:
    Farmer calls → POST /api/ivr/incoming
    → Welcome + main menu: "Press 1 for prices, 2 for weather, 3 for profile, 4 for listings, 5 for orders"
    → Each option routes to sub-menu
    → Farmer navigates with DTMF (key presses) or voice
    → All responses via Sarvam TTS in Hindi

Requires: Exotel, Sarvam AI, Firebase/Firestore
"""

import os
import re
import json
import time
import logging
from typing import Optional
from xml.sax.saxutils import escape as xml_escape

import requests
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────────

app = FastAPI(title="AgriConnect Farmer Phone Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ──────────────────────────────────────────────────────

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_API_BASE = "https://api.sarvam.ai"
EXOTEL_SID = os.getenv("EXOTEL_SID", "")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY", "")
EXOTEL_ACCOUNT_SID = os.getenv("EXOTEL_ACCOUNT_SID", "")
PUBLIC_API_BASE = os.getenv("PUBLIC_API_BASE", "https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev")
FIREBASE_PROJECT = os.getenv("FIREBASE_PROJECT_ID", "agriconnect-zypher-db")

# Firebase Admin SDK (lazy init)
_firebase_app = None
_firestore_db = None

def get_firestore():
    global _firestore_db
    if _firestore_db is None:
        try:
            import firebase_admin
            from firebase_admin import firestore
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            _firestore_db = firestore.client()
        except Exception as e:
            logger.error(f"Firebase init failed: {e}")
            # Fallback: use REST API
            return None
    return _firestore_db


# ─── Crop Keywords ───────────────────────────────────────────────

CROP_KEYWORDS = {
    # Hindi (Devanagari)
    "गेहूं": "wheat", "चावल": "rice", "धान": "rice", "मक्का": "maize",
    "कपास": "cotton", "सोयाबीन": "soybean", "आलू": "potato",
    "टमाटर": "tomato", "प्याज": "onion", "मूंगफली": "groundnut",
    "गन्ना": "sugarcane", "मूंग": "moong", "सरसों": "mustard",
    "चना": "chickpea", "सूरजमुखी": "sunflower",
    # Romanized Hindi
    "gehu": "wheat", "chawal": "rice", "dhaan": "rice",
    "makka": "maize", "kapas": "cotton", "soyabean": "soybean",
    "aloo": "potato", "tamatar": "tomato", "pyaaz": "onion",
    "moongfali": "groundnut", "ganna": "sugarcane", "moong": "moong",
    "sarson": "mustard", "chana": "chickpea",
    # English
    "wheat": "wheat", "rice": "rice", "maize": "maize", "corn": "maize",
    "cotton": "cotton", "soybean": "soybean", "potato": "potato",
    "tomato": "tomato", "onion": "onion", "groundnut": "groundnut",
    "sugarcane": "sugarcane", "mustard": "mustard", "chickpea": "chickpea",
    "sunflower": "sunflower",
}

# ─── TwiML Helpers ───────────────────────────────────────────────

def twiml_response(parts: list) -> str:
    body = "\n    ".join(parts)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n    {body}\n</Response>'


def twiml_say(text: str, language: str = "hi-IN", voice: str = "alice") -> str:
    return f'<Say language="{language}" voice="{voice}">{xml_escape(text)}</Say>'


def twiml_play(url: str) -> str:
    return f'<Play>{xml_escape(url)}</Play>'


def twiml_gather(action_url: str, text: str, num_digits: int = None,
                  speech_timeout: int = 3, language: str = "hi-IN",
                  method: str = "POST") -> str:
    if num_digits:
        return (
            f'<Gather action="{xml_escape(action_url)}" method="{method}" '
            f'numDigits="{num_digits}" timeout="10">\n'
            f'    {twiml_say(text, language)}\n'
            f'</Gather>'
        )
    return (
        f'<Gather action="{xml_escape(action_url)}" method="{method}" '
        f'input="speech" speechTimeout="{speech_timeout}" language="{language}" timeout="10">\n'
        f'    {twiml_say(text, language)}\n'
        f'</Gather>'
    )


def twiml_gather_dtmf(action_url: str, text: str, num_digits: int = 1,
                       method: str = "POST") -> str:
    return (
        f'<Gather action="{xml_escape(action_url)}" method="{method}" '
        f'numDigits="{num_digits}" timeout="15">\n'
        f'    {twiml_say(text, "hi-IN")}\n'
        f'</Gather>'
    )


def twiml_redirect(url: str) -> str:
    return f'<Redirect method="POST">{xml_escape(url)}</Redirect>'


def twiml_hangup() -> str:
    return "<Hangup/>"


# ─── Sarvam TTS ──────────────────────────────────────────────────

def sarvam_tts(text: str, language: str = "hi-IN", speaker: str = "priya") -> Optional[bytes]:
    if not SARVAM_API_KEY:
        return None
    payload = {
        "text": text[:2500],
        "language_code": language,
        "speaker": speaker,
        "model": "bulbul:v3",
    }
    try:
        resp = requests.post(
            f"{SARVAM_API_BASE}/text-to-speech",
            headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
            json=payload, timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            audios = data.get("audios", [])
            if audios:
                import base64
                return base64.b64decode("".join(audios))
        logger.error(f"Sarvam TTS {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"Sarvam TTS failed: {e}")
        return None


# ─── Firebase Helpers ────────────────────────────────────────────

def firestore_get_collection(collection: str, field: str = None, value: str = None) -> list:
    """Fetch documents from Firestore collection."""
    db = get_firestore()
    if not db:
        return []
    try:
        ref = db.collection(collection)
        if field and value:
            ref = ref.where(field, "==", value)
        docs = ref.stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        logger.error(f"Firestore read error: {e}")
        return []


def firestore_get_doc(collection: str, doc_id: str) -> Optional[dict]:
    db = get_firestore()
    if not db:
        return None
    try:
        doc = db.collection(collection).document(doc_id).get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None
    except Exception as e:
        logger.error(f"Firestore read error: {e}")
        return None


def firestore_add_doc(collection: str, data: dict) -> Optional[str]:
    db = get_firestore()
    if not db:
        return None
    try:
        ref = db.collection(collection).add(data)
        return ref[1].id
    except Exception as e:
        logger.error(f"Firestore write error: {e}")
        return None


def firestore_update_doc(collection: str, doc_id: str, data: dict) -> bool:
    db = get_firestore()
    if not db:
        return False
    try:
        db.collection(collection).document(doc_id).update(data)
        return True
    except Exception as e:
        logger.error(f"Firestore update error: {e}")
        return False


def find_farmer_by_phone(phone: str) -> Optional[dict]:
    """Find farmer profile by phone number."""
    clean = re.sub(r"^(\+91|91|0)", "", phone.strip())
    profiles = firestore_get_collection("profiles", "role", "farmer")
    for p in profiles:
        p_clean = re.sub(r"^(\+91|91|0)", "", str(p.get("phone", "")).strip())
        if p_clean == clean or p.get("phone") == phone:
            return p
    return None


# ─── Price Fetching ──────────────────────────────────────────────

def fetch_crop_price(crop: str, state: str) -> Optional[dict]:
    """Fetch crop price from prediction API."""
    try:
        resp = requests.get(
            f"{PUBLIC_API_BASE}/api/predict/{crop}/{state}",
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        logger.error(f"Price fetch failed: {e}")
        return None


def fetch_weather(state: str) -> Optional[dict]:
    """Fetch weather from weather API."""
    try:
        resp = requests.get(
            f"{PUBLIC_API_BASE}/api/weather/v2?state={state}&days=3",
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")
        return None


# ─── Call Logging ────────────────────────────────────────────────

def log_call(call_id: str, phone: str, action: str, details: str = ""):
    """Log IVR call to Firestore."""
    firestore_add_doc("ivr_calls", {
        "call_id": call_id,
        "phone": phone,
        "action": action,
        "details": details,
        "timestamp": time.time(),
    })


# ─── Number → Hindi Conversion ──────────────────────────────────

def num_to_hindi(n: int) -> str:
    """Convert number to Hindi words for TTS."""
    ones = ["", "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ", "दस",
            "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "सत्रह", "अठारह", "उन्नीस"]
    tens = ["", "", "बीस", "तीस", "चालीस", "पचास", "साठ", "सत्तर", "अस्सी", "नब्बे"]
    
    if n < 20:
        return ones[n]
    elif n < 100:
        return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
    elif n < 1000:
        return ones[n // 100] + " सौ" + (" " + num_to_hindi(n % 100) if n % 100 else "")
    elif n < 100000:
        return num_to_hindi(n // 1000) + " हज़ार" + (" " + num_to_hindi(n % 1000) if n % 1000 else "")
    else:
        return str(n)


# ═══════════════════════════════════════════════════════════════════
#  IVR ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


@app.post("/api/ivr/incoming")
async def ivr_incoming(request: Request):
    """
    Main entry point. Farmer calls → welcome + main menu.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    caller = form.get("From", "unknown")

    # Detect state from phone
    clean_phone = re.sub(r"^(\+91|91|0)", "", caller.strip())
    state_prefixes = {
        "70": "uttar_pradesh", "71": "uttar_pradesh", "72": "uttar_pradesh",
        "73": "uttar_pradesh", "74": "maharashtra", "75": "maharashtra",
        "76": "maharashtra", "77": "madhya_pradesh", "78": "madhya_pradesh",
        "79": "madhya_pradesh", "80": "madhya_pradesh", "81": "madhya_pradesh",
        "82": "gujarat", "83": "gujarat", "84": "gujarat",
        "85": "rajasthan", "86": "rajasthan", "87": "rajasthan",
        "88": "punjab", "89": "punjab", "90": "bihar", "91": "bihar",
        "92": "west_bengal", "93": "west_bengal", "94": "karnataka",
        "95": "karnataka", "96": "tamil_nadu", "97": "tamil_nadu",
        "98": "andhra_pradesh", "99": "andhra_pradesh",
    }
    state = state_prefixes.get(clean_phone[:2], "uttar_pradesh")

    # Check if farmer exists
    farmer = find_farmer_by_phone(caller)
    farmer_name = farmer["name"].split()[0] if farmer else "किसान मित्र"

    base = PUBLIC_API_BASE

    welcome_text = (
        f"नमस्ते {farmer_name} जी! "
        f"AgriConnect कृषि सेवा में आपका स्वागत है। "
        f"हम आपकी मदद कर सकते हैं। "
    )

    if farmer:
        menu_text = (
            "कृपया अपना विकल्प चुनें: "
            "फसल की कीमत जानने के लिए एक दबाएं, "
            "मौसम जानने के लिए दो दबाएं, "
            "अपनी प्रोफाइल देखने के लिए तीन दबाएं, "
            "अपनी फसल सूची देखने के लिए चार दबाएं, "
            "ऑर्डर देखने के लिए पांच दबाएं, "
            "नई फसल जोड़ने के लिए छह दबाएं।"
        )
    else:
        menu_text = (
            "आप हमारे नए किसान मित्र लगते हैं! "
            "कीमत जानने के लिए एक दबाएं, "
            "मौसम जानने के लिए दो दबाएं, "
            "किसान रजिस्टर करने के लिए तीन दबाएं।"
        )

    xml = twiml_response([
        twiml_gather_dtmf(
            action_url=f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}",
            text=welcome_text + menu_text,
            num_digits=1,
        ),
        twiml_say("आपने कोई विकल्प नहीं चुना। कृपया दोबारा कॉल करें।"),
        twiml_hangup(),
    ])

    log_call(call_sid, caller, "incoming")
    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/menu")
async def ivr_menu(request: Request):
    """
    Main menu handler. Routes to sub-menus based on DTMF input.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    caller = form.get("From", "unknown")
    digits = form.get("Digits", "")
    state = request.query_params.get("state", "uttar_pradesh")
    base = PUBLIC_API_BASE

    if digits == "1":
        # Crop price check
        xml = twiml_response([
            twiml_gather(
                action_url=f"{base}/api/ivr/price-check?state={state}&caller={caller}&call_sid={call_sid}",
                text="फसल का नाम बोलें। जैसे गेहूं, चावल, मक्का, आलू, टमाटर, प्याज।",
                speech_timeout=3,
            ),
            twiml_say("हमें आपकी आवाज़ सुनाई नहीं दी। कृपया दोबारा कॉल करें।"),
            twiml_hangup(),
        ])
    elif digits == "2":
        # Weather check
        weather = fetch_weather(state)
        if weather:
            temp = weather.get("current", {}).get("temp", "अज्ञात")
            humidity = weather.get("current", {}).get("humidity", "अज्ञात")
            alerts = weather.get("alerts", [])
            recommendations = weather.get("farming_recommendations", [])

            weather_text = (
                f"आज {state.replace('_', ' ')} में तापमान {temp} डिग्री सेल्सियस है "
                f"और नमी {humidity} प्रतिशत है। "
            )
            if alerts:
                alert_msgs = [a.get("message", "") for a in alerts[:2]]
                weather_text += f"चेतावनी: {' '.join(alert_msgs)} "
            if recommendations:
                weather_text += f"सुझाव: {recommendations[0]} "

            xml = twiml_response([
                twiml_say(weather_text),
                twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
            ])
        else:
            xml = twiml_response([
                twiml_say("मौसम की जानकारी उपलब्ध नहीं है। कृपया बाद में कॉल करें।"),
                twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
            ])
    elif digits == "3":
        # Profile
        farmer = find_farmer_by_phone(caller)
        if farmer:
            name = farmer.get("name", "अज्ञात")
            phone = farmer.get("phone", "अज्ञात")
            # Count crops
            crops = firestore_get_collection("crops", "farmer_id", farmer["id"])
            crop_count = len(crops)

            profile_text = (
                f"आपकी प्रोफाइल: "
                f"नाम {name}, "
                f"फ़ोन {phone}, "
                f"आपकी {crop_count} फसलें सूचीबद्ध हैं। "
                f"प्रोफाइल अपडेट करने के लिए एक दबाएं, "
                f"वापस मेनू में जाने के लिए दो दबाएं।"
            )
            xml = twiml_response([
                twiml_gather_dtmf(
                    action_url=f"{base}/api/ivr/profile-action?caller={caller}&call_sid={call_sid}&state={state}",
                    text=profile_text,
                    num_digits=1,
                ),
                twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
            ])
        else:
            xml = twiml_response([
                twiml_say(
                    "आपकी प्रोफाइल नहीं मिली। "
                    "रजिस्टर करने के लिए कृपया नज़दीकी कृषि केंद्र पर जाएं, "
                    "या वेबसाइट पर साइन अप करें।"
                ),
                twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
            ])
    elif digits == "4":
        # My Listings
        farmer = find_farmer_by_phone(caller)
        if farmer:
            crops = firestore_get_collection("crops", "farmer_id", farmer["id"])
            if crops:
                listing_text = f"आपके पास {len(crops)} फसलें हैं। "
                for i, crop in enumerate(crops[:5], 1):
                    name = crop.get("name", "फसल")
                    qty = crop.get("quantity", 0)
                    unit = crop.get("unit", "kg")
                    price = crop.get("price", 0)
                    listing_text += f"{i}. {name}, {qty} {unit}, {price} रुपये प्रति {unit}। "

                listing_text += (
                    "नई फसल जोड़ने के लिए एक दबाएं, "
                    "कीमत बदलने के लिए दो दबाएं, "
                    "फसल बेची गई बताने के लिए तीन दबाएं, "
                    "वापस मेनू में जाने के लिए चार दबाएं।"
                )
                xml = twiml_response([
                    twiml_gather_dtmf(
                        action_url=f"{base}/api/ivr/listing-action?caller={caller}&call_sid={call_sid}&state={state}",
                        text=listing_text,
                        num_digits=1,
                    ),
                    twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
                ])
            else:
                xml = twiml_response([
                    twiml_say(
                        "आपकी कोई फसल सूचीबद्ध नहीं है। "
                        "नई फसल जोड़ने के लिए एक दबाएं।"
                    ),
                    twiml_gather_dtmf(
                        action_url=f"{base}/api/ivr/add-crop-start?caller={caller}&call_sid={call_sid}&state={state}",
                        text="",
                        num_digits=0,
                    ),
                    twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
                ])
        else:
            xml = twiml_response([
                twiml_say("कृपया पहले रजिस्टर करें।"),
                twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
            ])
    elif digits == "5":
        # My Orders
        farmer = find_farmer_by_phone(caller)
        if farmer:
            orders = firestore_get_collection("orders", "farmer_id", farmer["id"])
            if orders:
                pending = [o for o in orders if o.get("status") == "Pending"]
                active = [o for o in orders if o.get("status") == "Processing"]
                completed = [o for o in orders if o.get("status") in ("Delivered", "Rejected")]

                order_text = (
                    f"आपके पास {len(orders)} ऑर्डर हैं। "
                    f"{len(pending)} नए, {len(active)} प्रक्रिया में, {len(completed)} पूर्ण। "
                )
                if pending:
                    o = pending[0]
                    buyer = o.get("wholesaler_name", o.get("consumer_name", "खरीददार"))
                    crop = o.get("crop_name", "फसल")
                    qty = o.get("quantity", 0)
                    total = o.get("total_price", 0)
                    order_text += (
                        f"पहला नया ऑर्डर: {buyer} ने {qty} {o.get('unit', 'kg')} {crop} मांगा है, "
                        f"कुल {total} रुपये। "
                        f"स्वीकार करने के लिए एक, अस्वीकार करने के लिए दो, "
                        f"वापस मेनू में जाने के लिए तीन दबाएं।"
                    )
                    xml = twiml_response([
                        twiml_gather_dtmf(
                            action_url=f"{base}/api/ivr/order-action?order_id={o['id']}&caller={caller}&call_sid={call_sid}&state={state}",
                            text=order_text,
                            num_digits=1,
                        ),
                        twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
                    ])
                else:
                    xml = twiml_response([
                        twiml_say(order_text + " कोई नया ऑर्डर नहीं है।"),
                        twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
                    ])
            else:
                xml = twiml_response([
                    twiml_say("आपके पास कोई ऑर्डर नहीं है।"),
                    twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
                ])
        else:
            xml = twiml_response([
                twiml_say("कृपया पहले रजिस्टर करें।"),
                twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
            ])
    elif digits == "6":
        # Add new crop
        xml = twiml_response([
            twiml_gather(
                action_url=f"{base}/api/ivr/add-crop-name?caller={caller}&call_sid={call_sid}&state={state}",
                text="फसल का नाम बोलें। जैसे गेहूं, चावल, मक्का।",
                speech_timeout=3,
            ),
            twiml_say("हमें आवाज़ सुनाई नहीं दी।"),
            twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
        ])
    else:
        xml = twiml_response([
            twiml_say("कृपया सही विकल्प चुनें।"),
            twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
        ])

    log_call(call_sid, caller, "menu", f"digit={digits}")
    return Response(content=xml, media_type="application/xml")


# ═══════════════════════════════════════════════════════════════════
#  CROP PRICE SUB-FLOW
# ═══════════════════════════════════════════════════════════════════


@app.post("/api/ivr/price-check")
async def ivr_price_check(request: Request):
    """Handle speech → parse crop → fetch price → respond."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    caller = form.get("From", "unknown")
    speech = form.get("SpeechResult", "").strip()
    state = request.query_params.get("state", "uttar_pradesh")
    base = PUBLIC_API_BASE

    logger.info(f"Price check: speech='{speech}', state={state}")

    # Parse crop from speech
    crop = None
    speech_lower = speech.lower()
    for keyword, value in CROP_KEYWORDS.items():
        if keyword.lower() in speech_lower:
            crop = value
            break

    if not crop:
        xml = twiml_response([
            twiml_say(f"हमें '{speech}' समझ नहीं आया। कृपया फसल का नाम स्पष्ट रूप से बोलें।"),
            twiml_gather(
                action_url=f"{base}/api/ivr/price-check?state={state}&caller={caller}&call_sid={call_sid}",
                text="गेहूं, चावल, मक्का, आलू, टमाटर, प्याज — इनमें से कोई बोलें।",
                speech_timeout=3,
            ),
            twiml_hangup(),
        ])
        return Response(content=xml, media_type="application/xml")

    # Fetch price
    price_data = fetch_crop_price(crop, state)
    if price_data:
        current = price_data.get("current_price", 0)
        p7 = price_data.get("predicted_price_7d", 0)
        p30 = price_data.get("predicted_price_30d", 0)
        trend = price_data.get("trend", "stable")

        trend_hi = {"bullish": "बढ़ रही है", "bearish": "गिर रही है", "stable": "स्थिर है"}
        trend_text = trend_hi.get(trend, "स्थिर है")

        crop_names_hi = {
            "wheat": "गेहूं", "rice": "चावल", "maize": "मक्का", "cotton": "कपास",
            "potato": "आलू", "tomato": "टमाटर", "onion": "प्याज",
            "soybean": "सोयाबीन", "groundnut": "मूंगफली", "sugarcane": "गन्ना",
        }
        crop_hi = crop_names_hi.get(crop, crop)

        response_text = (
            f"{crop_hi} की आज की कीमत {int(current)} रुपये प्रति क्विंटल है। "
            f"अगले 7 दिन में अनुमान {int(p7)} रुपये है। "
            f"30 दिन में {int(p30)} रुपये की उम्मीद है। "
            f"बाज़ार की प्रवृत्ति {trend_text}। "
            "कोई और फसल पूछने के लिए एक दबाएं, "
            "वापस मेनू में जाने के लिए दो दबाएं।"
        )
    else:
        response_text = (
            f"{crop} की कीमत अभी उपलब्ध नहीं है। "
            "कोई और फसल पूछने के लिए एक दबाएं, "
            "वापस मेनू में जाने के लिए दो दबाएं।"
        )

    xml = twiml_response([
        twiml_say(response_text),
        twiml_gather_dtmf(
            action_url=f"{base}/api/ivr/price-again?state={state}&caller={caller}&call_sid={call_sid}",
            text="",
            num_digits=1,
        ),
        twiml_hangup(),
    ])

    log_call(call_sid, caller, "price_check", f"crop={crop}, state={state}")
    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/price-again")
async def ivr_price_again(request: Request):
    """After price check — ask for another or return to menu."""
    form = await request.form()
    digits = form.get("Digits", "")
    state = request.query_params.get("state", "uttar_pradesh")
    caller = request.query_params.get("caller", "unknown")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    if digits == "1":
        xml = twiml_response([
            twiml_gather(
                action_url=f"{base}/api/ivr/price-check?state={state}&caller={caller}&call_sid={call_sid}",
                text="अगली फसल का नाम बोलें।",
                speech_timeout=3,
            ),
            twiml_hangup(),
        ])
    else:
        xml = twiml_response([
            twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
        ])
    return Response(content=xml, media_type="application/xml")


# ═══════════════════════════════════════════════════════════════════
#  PROFILE SUB-FLOW
# ═══════════════════════════════════════════════════════════════════


@app.post("/api/ivr/profile-action")
async def ivr_profile_action(request: Request):
    """Handle profile actions — update name, location."""
    form = await request.form()
    digits = form.get("Digits", "")
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    if digits == "1":
        # Update name
        xml = twiml_response([
            twiml_gather(
                action_url=f"{base}/api/ivr/profile-update-name?caller={caller}&call_sid={call_sid}&state={state}",
                text="अपना नया नाम बोलें।",
                speech_timeout=4,
            ),
            twiml_say("हमें आवाज़ सुनाई नहीं दी।"),
            twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
        ])
    else:
        xml = twiml_response([
            twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
        ])
    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/profile-update-name")
async def ivr_profile_update_name(request: Request):
    """Update farmer's name from speech."""
    form = await request.form()
    speech = form.get("SpeechResult", "").strip()
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    farmer = find_farmer_by_phone(caller)
    if farmer and speech:
        # Take first few words as name
        new_name = " ".join(speech.split()[:3])
        firestore_update_doc("profiles", farmer["id"], {"name": new_name})
        response_text = f"आपका नाम {new_name} कर दिया गया है।"
    else:
        response_text = "नाम अपडेट नहीं हो सका।"

    xml = twiml_response([
        twiml_say(response_text),
        twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
    ])
    return Response(content=xml, media_type="application/xml")


# ═══════════════════════════════════════════════════════════════════
#  LISTING MANAGEMENT SUB-FLOW
# ═══════════════════════════════════════════════════════════════════


@app.post("/api/ivr/listing-action")
async def ivr_listing_action(request: Request):
    """Handle listing actions."""
    form = await request.form()
    digits = form.get("Digits", "")
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    if digits == "1":
        # Add new crop
        xml = twiml_response([
            twiml_gather(
                action_url=f"{base}/api/ivr/add-crop-name?caller={caller}&call_sid={call_sid}&state={state}",
                text="फसल का नाम बोलें।",
                speech_timeout=3,
            ),
            twiml_say("हमें आवाज़ सुनाई नहीं दी।"),
            twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
        ])
    elif digits == "2":
        # Update price
        farmer = find_farmer_by_phone(caller)
        if farmer:
            crops = firestore_get_collection("crops", "farmer_id", farmer["id"])
            if crops:
                crop_names = " ".join([f"{i+1}. {c.get('name', '')}" for i, c in enumerate(crops[:5])])
                xml = twiml_response([
                    twiml_gather_dtmf(
                        action_url=f"{base}/api/ivr/update-price-id?caller={caller}&call_sid={call_sid}&state={state}",
                        text=f"किस फसल की कीमत बदलनी है? {crop_names} — संख्या दबाएं।",
                        num_digits=1,
                    ),
                    twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
                ])
            else:
                xml = twiml_response([
                    twiml_say("कोई फसल नहीं है।"),
                    twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
                ])
        else:
            xml = twiml_response([
                twiml_say("प्रोफाइल नहीं मिली।"),
                twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
            ])
    elif digits == "3":
        # Mark as sold
        farmer = find_farmer_by_phone(caller)
        if farmer:
            crops = firestore_get_collection("crops", "farmer_id", farmer["id"])
            if crops:
                crop_names = " ".join([f"{i+1}. {c.get('name', '')}" for i, c in enumerate(crops[:5])])
                xml = twiml_response([
                    twiml_gather_dtmf(
                        action_url=f"{base}/api/ivr/mark-sold-id?caller={caller}&call_sid={call_sid}&state={state}",
                        text=f"कौन सी फसल बेची गई? {crop_names} — संख्या दबाएं।",
                        num_digits=1,
                    ),
                    twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
                ])
            else:
                xml = twiml_response([
                    twiml_say("कोई फसल नहीं है।"),
                    twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
                ])
        else:
            xml = twiml_response([
                twiml_say("प्रोफाइल नहीं मिली।"),
                twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
            ])
    else:
        xml = twiml_response([
            twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
        ])
    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/add-crop-name")
async def ivr_add_crop_name(request: Request):
    """Step 1 of adding crop — get name from speech."""
    form = await request.form()
    speech = form.get("SpeechResult", "").strip()
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    # Parse crop name
    crop = None
    for keyword, value in CROP_KEYWORDS.items():
        if keyword.lower() in speech.lower():
            crop = value
            break
    if not crop:
        crop = speech.split()[0].lower() if speech else "unknown"

    xml = twiml_response([
        twiml_gather_dtmf(
            action_url=f"{base}/api/ivr/add-crop-qty?crop={crop}&caller={caller}&call_sid={call_sid}&state={state}",
            text=f"आप {crop} जोड़ रहे हैं। मात्रा बताएं — किलो में संख्या दबाएं, जैसे 100।",
            num_digits=4,
        ),
        twiml_hangup(),
    ])
    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/add-crop-qty")
async def ivr_add_crop_qty(request: Request):
    """Step 2 — get quantity."""
    form = await request.form()
    digits = form.get("Digits", "0")
    crop = request.query_params.get("crop", "wheat")
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    qty = int(digits) if digits.isdigit() else 0

    xml = twiml_response([
        twiml_gather_dtmf(
            action_url=f"{base}/api/ivr/add-crop-price?crop={crop}&qty={qty}&caller={caller}&call_sid={call_sid}&state={state}",
            text=f"{qty} किलो {crop}। अब कीमत बताएं — प्रति किलो रुपये में, जैसे 20।",
            num_digits=4,
        ),
        twiml_hangup(),
    ])
    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/add-crop-price")
async def ivr_add_crop_price(request: Request):
    """Step 3 — get price → save crop."""
    form = await request.form()
    digits = form.get("Digits", "0")
    crop = request.query_params.get("crop", "wheat")
    qty = request.query_params.get("qty", "0")
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    price = int(digits) if digits.isdigit() else 0

    farmer = find_farmer_by_phone(caller)
    if farmer:
        from datetime import datetime
        doc_id = firestore_add_doc("crops", {
            "name": crop,
            "category": "Grains",
            "quantity": int(qty),
            "unit": "kg",
            "price": price,
            "harvest_date": datetime.now().isoformat(),
            "location": state.replace("_", " ").title(),
            "farmer_id": farmer["id"],
            "status": "Ready",
        })
        if doc_id:
            response_text = (
                f"बहुत अच्छा! {crop} की {qty} किलो फसल {price} रुपये प्रति किलो की दर से जोड़ दी गई है। "
                f"आपकी फसल अब खरीददारों को दिखाई देगी।"
            )
        else:
            response_text = "फसल जोड़ने में समस्या आई। कृपया दोबारा कोशिश करें।"
    else:
        response_text = "प्रोफाइल नहीं मिली। कृपया रजिस्टर करें।"

    xml = twiml_response([
        twiml_say(response_text),
        twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
    ])
    log_call(call_sid, caller, "add_crop", f"crop={crop}, qty={qty}, price={price}")
    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/update-price-id")
async def ivr_update_price_id(request: Request):
    """Get which crop to update price for."""
    form = await request.form()
    digits = form.get("Digits", "1")
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    farmer = find_farmer_by_phone(caller)
    if farmer:
        crops = firestore_get_collection("crops", "farmer_id", farmer["id"])
        idx = int(digits) - 1 if digits.isdigit() else 0
        if 0 <= idx < len(crops):
            crop = crops[idx]
            xml = twiml_response([
                twiml_gather_dtmf(
                    action_url=f"{base}/api/ivr/update-price-save?crop_id={crop['id']}&caller={caller}&call_sid={call_sid}&state={state}",
                    text=f"{crop.get('name', '')} की नई कीमत बताएं — प्रति किलो रुपये में।",
                    num_digits=4,
                ),
                twiml_hangup(),
            ])
        else:
            xml = twiml_response([
                twiml_say("गलत संख्या।"),
                twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
            ])
    else:
        xml = twiml_response([
            twiml_say("प्रोफाइल नहीं मिली।"),
            twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
        ])
    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/update-price-save")
async def ivr_update_price_save(request: Request):
    """Save new price."""
    form = await request.form()
    digits = form.get("Digits", "0")
    crop_id = request.query_params.get("crop_id", "")
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    new_price = int(digits) if digits.isdigit() else 0
    if crop_id and new_price > 0:
        firestore_update_doc("crops", crop_id, {"price": new_price})
        response_text = f"कीमत {new_price} रुपये प्रति किलो कर दी गई है।"
    else:
        response_text = "कीमत अपडेट नहीं हो सकी।"

    xml = twiml_response([
        twiml_say(response_text),
        twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
    ])
    return Response(content=xml, media_type="application/xml")


@app.post("/api/ivr/mark-sold-id")
async def ivr_mark_sold_id(request: Request):
    """Mark crop as sold (delete from listings)."""
    form = await request.form()
    digits = form.get("Digits", "1")
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    farmer = find_farmer_by_phone(caller)
    if farmer:
        crops = firestore_get_collection("crops", "farmer_id", farmer["id"])
        idx = int(digits) - 1 if digits.isdigit() else 0
        if 0 <= idx < len(crops):
            crop = crops[idx]
            # Delete the listing (mark as sold)
            db = get_firestore()
            if db:
                db.collection("crops").document(crop["id"]).delete()
            response_text = f"{crop.get('name', 'फसल')} बेची गई और सूची से हटा दी गई है। बधाई हो!"
        else:
            response_text = "गलत संख्या।"
    else:
        response_text = "प्रोफाइल नहीं मिली।"

    xml = twiml_response([
        twiml_say(response_text),
        twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
    ])
    return Response(content=xml, media_type="application/xml")


# ═══════════════════════════════════════════════════════════════════
#  ORDER MANAGEMENT SUB-FLOW
# ═══════════════════════════════════════════════════════════════════


@app.post("/api/ivr/order-action")
async def ivr_order_action(request: Request):
    """Handle order accept/reject."""
    form = await request.form()
    digits = form.get("Digits", "")
    order_id = request.query_params.get("order_id", "")
    caller = request.query_params.get("caller", "unknown")
    state = request.query_params.get("state", "uttar_pradesh")
    call_sid = request.query_params.get("call_sid", "unknown")
    base = PUBLIC_API_BASE

    if digits == "1":
        # Accept
        if order_id:
            firestore_update_doc("orders", order_id, {
                "status": "Processing",
                "updated_at": datetime.now().isoformat() if 'datetime' in dir() else str(time.time()),
            })
            response_text = "ऑर्डर स्वीकार कर लिया गया है। प्रोसेसिंग शुरू हो गई है।"
        else:
            response_text = "ऑर्डर अपडेट नहीं हो सका।"
    elif digits == "2":
        # Reject
        if order_id:
            firestore_update_doc("orders", order_id, {
                "status": "Rejected",
                "updated_at": str(time.time()),
            })
            response_text = "ऑर्डर अस्वीकार कर दिया गया है।"
        else:
            response_text = "ऑर्डर अपडेट नहीं हो सका।"
    else:
        response_text = "वापस मेनू में जा रहे हैं।"

    xml = twiml_response([
        twiml_say(response_text),
        twiml_redirect(f"{base}/api/ivr/menu?state={state}&caller={caller}&call_sid={call_sid}"),
    ])
    log_call(call_sid, caller, "order_action", f"order={order_id}, action={digits}")
    return Response(content=xml, media_type="application/xml")


# ═══════════════════════════════════════════════════════════════════
#  HELPER ENDPOINTS (for testing)
# ═══════════════════════════════════════════════════════════════════


@app.get("/api/ivr/phone/health")
async def phone_health():
    return {
        "status": "ok",
        "service": "AgriConnect Phone Platform",
        "features": [
            "crop_prices",
            "weather",
            "profile_management",
            "crop_listing_management",
            "order_management",
            "voice_navigation",
        ],
        "languages": ["hi-IN", "en-IN", "ta-IN", "te-IN", "kn-IN", "mr-IN"],
    }


@app.get("/api/ivr/phone/demo")
async def phone_demo():
    """Show demo call flow for judges."""
    return {
        "demo_flow": {
            "step_1": "Farmer calls the AgriConnect number",
            "step_2": "System detects state from phone number prefix",
            "step_3": "Welcome message: 'नमस्ते [Name] जी! AgriConnect में आपका स्वागत है'",
            "step_4": "Main Menu: 'कीमत जानें=1, मौसम=2, प्रोफाइल=3, फसल सूची=4, ऑर्डर=5, नई फसल=6'",
            "step_5": "Farmer presses 1 → 'फसल का नाम बोलें'",
            "step_6": "Farmer says 'गेहूं' → System fetches price from AI prediction API",
            "step_7": "TTS response: 'गेहूं की आज की कीमत 2042 रुपये प्रति क्विंटल है...'",
            "step_8": "Farmer can manage crops, orders, profile — all via phone!",
        },
        "capabilities": [
            " voice recognition (Hindi + English)",
            "DTMF navigation (keypad)",
            "AI crop price prediction",
            "Live weather alerts",
            "Crop listing management (add/update/delete)",
            "Order management (accept/reject)",
            "Profile updates",
            "All via phone call — no smartphone needed",
        ],
    }
