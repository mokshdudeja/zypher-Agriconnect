"""
AgriConnect — Voice Agent API Tools

These endpoints are called by the Sarvam Voice Agent as "API tools"
during phone conversations with farmers.
"""

import os
import json
import logging
import urllib.parse
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(title="AgriConnect Voice Tools")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ──────────────────────────────────────────────────────

API_BASE = os.getenv("API_BASE_URL", "https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev")
FIREBASE_PROJECT = os.getenv("FIREBASE_PROJECT_ID", "agriconnect-zypher-db")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "AIzaSyCPqo6OEr8UwJV1RXce0It-ZR2Fjjz_WIo")

# ─── Firestore REST API Helper ───────────────────────────────────

def _firestore_get(collection, doc_id=None):
    """Fetch a document or list from Firestore via REST API."""
    base = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT}/databases/(default)/documents"
    if doc_id:
        url = f"{base}/{collection}/{doc_id}?key={FIREBASE_API_KEY}"
    else:
        url = f"{base}/{collection}?key={FIREBASE_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"Firestore GET {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"Firestore GET error: {e}")
        return None


def _firestore_query(collection, field, op, value, limit=10):
    """Run a structured query on Firestore via REST API."""
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT}/databases/(default)/documents/{collection}?key={FIREBASE_API_KEY}"
    body = {
        "structuredQuery": {
            "from": [{"collectionId": collection}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": field},
                    "op": op,
                    "value": {"stringValue": str(value)}
                }
            },
            "orderBy": [{"field": {"fieldPath": "created_at"}, "direction": "DESCENDING"}],
            "limit": limit
        }
    }
    try:
        resp = requests.post(url, json=body, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"Firestore QUERY {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"Firestore QUERY error: {e}")
        return None


def _firestore_set(collection, doc_id, data):
    """Write a document to Firestore via REST API."""
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT}/databases/(default)/documents/{collection}/{doc_id}?key={FIREBASE_API_KEY}"
    # Convert Python dict to Firestore REST format
    fields = {}
    for k, v in data.items():
        if isinstance(v, str):
            fields[k] = {"stringValue": v}
        elif isinstance(v, (int, float)):
            fields[k] = {"doubleValue": v}
        elif isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        else:
            fields[k] = {"stringValue": str(v)}
    body = {"fields": fields}
    try:
        resp = requests.patch(url, json=body, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Firestore SET error: {e}")
        return False


def _firestore_add(collection, data):
    """Add a new document to Firestore (auto-generated ID)."""
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT}/databases/(default)/documents/{collection}?key={FIREBASE_API_KEY}"
    fields = {}
    for k, v in data.items():
        if isinstance(v, str):
            fields[k] = {"stringValue": v}
        elif isinstance(v, (int, float)):
            fields[k] = {"doubleValue": v}
        elif isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        else:
            fields[k] = {"stringValue": str(v)}
    body = {"fields": fields}
    try:
        resp = requests.post(url, json=body, timeout=10)
        if resp.status_code == 200:
            name = resp.json().get("name", "")
            doc_id = name.split("/")[-1] if name else None
            return doc_id
        return None
    except Exception as e:
        logger.error(f"Firestore ADD error: {e}")
        return None


def _firestore_update(collection, doc_id, data):
    """Update fields in a Firestore document."""
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT}/databases/(default)/documents/{collection}/{doc_id}?key={FIREBASE_API_KEY}&updateMask.fieldPaths={','.join(data.keys())}"
    fields = {}
    for k, v in data.items():
        if isinstance(v, str):
            fields[k] = {"stringValue": v}
        elif isinstance(v, (int, float)):
            fields[k] = {"doubleValue": v}
        elif isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        else:
            fields[k] = {"stringValue": str(v)}
    body = {"fields": fields}
    try:
        resp = requests.patch(url, json=body, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Firestore UPDATE error: {e}")
        return False


def _parse_firestore_doc(doc):
    """Parse a Firestore REST API document into a Python dict."""
    if not doc or "fields" not in doc:
        return {}
    result = {}
    for k, v in doc["fields"].items():
        if "stringValue" in v:
            result[k] = v["stringValue"]
        elif "doubleValue" in v:
            result[k] = v["doubleValue"]
        elif "integerValue" in v:
            result[k] = int(v["integerValue"])
        elif "booleanValue" in v:
            result[k] = v["booleanValue"]
        elif "timestampValue" in v:
            result[k] = v["timestampValue"]
        elif "arrayValue" in v:
            result[k] = [item.get("stringValue", "") for item in v["arrayValue"].get("values", [])]
        elif "mapValue" in v:
            result[k] = _parse_firestore_doc(v["mapValue"])
    return result


def _parse_firestore_docs(response):
    """Parse multiple documents from a Firestore query response."""
    if not response or "documents" not in response:
        return []
    docs = []
    for doc in response["documents"]:
        doc_id = doc.get("name", "").split("/")[-1]
        fields = _parse_firestore_doc(doc)
        fields["id"] = doc_id
        docs.append(fields)
    return docs


def _resolve_farmer_id(phone: str) -> str:
    """Resolve phone → Firebase UID via phone_lookup collection."""
    normalized = phone.strip()
    if not normalized.startswith("+"):
        normalized = "+91" + normalized.lstrip("0")
    
    # Check phone_lookup
    doc = _firestore_get("phone_lookup", normalized)
    if doc:
        uid = doc.get("fields", {}).get("firebase_uid", {}).get("stringValue")
        if uid:
            logger.info(f"Resolved phone {normalized} → UID {uid}")
            return uid
    
    # Fallback: check profiles for matching phone
    result = _firestore_query("profiles", "phone", "EQUAL", normalized, limit=1)
    docs = _parse_firestore_docs(result)
    if docs:
        logger.info(f"Resolved phone {normalized} → UID {docs[0]['id']}")
        return docs[0]["id"]
    
    logger.info(f"No UID found for phone {normalized}, using phone as ID")
    return normalized


# ─── Tool 1: Crop Price Prediction ──────────────────────────────

@app.get("/api/voice-tools/price")
async def get_crop_price(
    crop: str = Query(..., description="Crop name in English or Hindi"),
    state: str = Query("uttar_pradesh", description="Indian state"),
    unit: str = Query("kg", description="Price unit"),
):
    CROP_MAP = {
        "गेहूं": "wheat", "gehu": "wheat", "wheat": "wheat",
        "चावल": "rice", "chawal": "rice", "rice": "rice",
        "मक्का": "maize", "makka": "maize", "corn": "maize",
        "कपास": "cotton", "kapas": "cotton",
        "सोयाबीन": "soybean", "soybean": "soybean",
        "आलू": "potato", "aloo": "potato",
        "टमाटर": "tomato", "tamatar": "tomato",
        "प्याज": "onion", "pyaz": "onion",
        "मूंगफली": "groundnut", "moongfali": "groundnut",
        "गन्ना": "sugarcane", "ganna": "sugarcane",
        "मूंग": "moong", "moong": "moong",
        "सरसों": "mustard", "sarson": "mustard",
        "चना": "chickpea", "chana": "chickpea",
    }
    STATE_MAP = {
        "उत्तर प्रदेश": "uttar_pradesh", "UP": "uttar_pradesh",
        "महाराष्ट्र": "maharashtra", "पंजाब": "punjab",
        "हरियाणा": "haryana", "मध्य प्रदेश": "madhya_pradesh",
        "राजस्थान": "rajasthan", "कर्नाटक": "karnataka",
        "तमिल नाडु": "tamil_nadu", "गुजरात": "gujarat",
        "पश्चिम बंगाल": "west_bengal", "बिहार": "bihar",
    }
    crop_slug = CROP_MAP.get(crop.strip(), crop.strip().lower().replace(" ", "_"))
    state_slug = STATE_MAP.get(state.strip(), state.strip().lower().replace(" ", "_"))
    try:
        resp = requests.get(f"{API_BASE}/api/predict/{crop_slug}/{state_slug}", params={"unit": unit}, timeout=15)
        data = resp.json()
        if "detail" in data:
            return {"error": data["detail"], "crop": crop, "state": state}
        crop_hi = {v: k for k, v in CROP_MAP.items()}.get(crop_slug, crop)
        return {
            "crop": crop_slug, "crop_hindi": crop_hi, "state": state_slug,
            "current_price": data.get("current_price"),
            "predicted_7d": data.get("predicted_price_7d"),
            "predicted_15d": data.get("predicted_price_15d"),
            "predicted_30d": data.get("predicted_price_30d"),
            "unit": data.get("unit", unit),
            "trend": data.get("trend"),
            "factors": data.get("factors", []),
            "confidence": data.get("confidence"),
            "message_hi": f"{crop_hi} की आज की कीमत {data.get('current_price', '?')} रुपये प्रति {unit} है।",
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Tool 2: Weather ─────────────────────────────────────────────

STATE_COORDS = {
    "uttar_pradesh": (26.8467, 80.9462), "maharashtra": (19.7515, 75.7139),
    "punjab": (31.1471, 75.3412), "haryana": (29.0588, 76.0856),
    "madhya_pradesh": (23.4735, 77.9470), "rajasthan": (27.0238, 74.2179),
    "karnataka": (15.3173, 75.7139), "tamil_nadu": (11.1271, 78.6569),
    "andhra_pradesh": (15.9129, 79.7400), "gujarat": (22.2587, 71.1924),
    "west_bengal": (22.9868, 87.8550), "bihar": (25.0961, 85.3131),
}
STATE_MAP_HI = {
    "uttar_pradesh": "उत्तर प्रदेश", "maharashtra": "महाराष्ट्र", "punjab": "पंजाब",
    "haryana": "हरियाणा", "madhya_pradesh": "मध्य प्रदेश", "rajasthan": "राजस्थान",
}

@app.get("/api/voice-tools/weather")
async def get_weather(state: str = Query(...), days: int = Query(3)):
    coords = STATE_COORDS.get(state.strip().lower().replace(" ", "_"))
    if not coords:
        return {"error": f"Unknown state: {state}"}
    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": coords[0], "longitude": coords[1],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "current": "temperature_2m,relative_humidity_2m",
            "timezone": "Asia/Kolkata", "forecast_days": min(days, 7),
        }, timeout=10)
        data = resp.json()
        daily = data.get("daily", {})
        current = data.get("current", {})
        alerts = []
        tips = []
        for i in range(len(daily.get("time", []))):
            tmax = daily["temperature_2m_max"][i]
            rain = daily["precipitation_sum"][i]
            if tmax > 42:
                alerts.append({"day": daily["time"][i], "type": "heatwave", "message": f"तापमान {tmax}°C — गर्मी की लहर!", "severity": "high"})
                tips.append("फसलों को सुबह जल्दी सींचें।")
            if rain > 50:
                alerts.append({"day": daily["time"][i], "type": "heavy_rain", "message": f"भारी बारिश {rain}mm!", "severity": "high"})
                tips.append("बारिश से पहले कटाई कर लें।")
        if not tips:
            tips.append("मौसम अनुकूल है। नियमित सिंचाई जारी रखें।")
        state_hi = STATE_MAP_HI.get(state, state)
        temp = current.get("temperature_2m", "?")
        hum = current.get("relative_humidity_2m", "?")
        return {
            "state": state, "state_hindi": state_hi,
            "current_temp": temp, "current_humidity": hum,
            "forecast": [{"date": daily["time"][i], "temp_max": daily["temperature_2m_max"][i], "temp_min": daily["temperature_2m_min"][i], "rain_mm": daily["precipitation_sum"][i]} for i in range(len(daily.get("time", [])))],
            "alerts": alerts, "farming_tips": tips,
            "message_hi": f"{state_hi} में अभी {temp}°C तापमान और {hum}% नमी है।",
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Tool 3: Crop Recommendation ────────────────────────────────

@app.get("/api/voice-tools/recommend")
async def get_crop_recommend(state: str = Query("uttar_pradesh"), soil_type: str = Query("loamy"), temperature: int = Query(25), rainfall: int = Query(800), season: str = Query("rabi")):
    try:
        resp = requests.post(f"{API_BASE}/api/crop-recommend", json={"soil_type": soil_type, "ph": 6.5, "nitrogen": 40, "phosphorus": 30, "potassium": 35, "rainfall": rainfall, "temperature": temperature, "season": season}, timeout=15)
        data = resp.json()
        recs = data.get("recommendations", [])[:3]
        return {
            "recommendations": [{"crop": r["crop"], "score": r["suitability_score"]} for r in recs],
            "message_hi": f"आपकी मिट्टी के लिए {', '.join([r['crop'] for r in recs[:3]])} उगाना अच्छा रहेगा।" if recs else "कोई सुझाव नहीं।",
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Tool 4: List Crop ──────────────────────────────────────────

class ListCropRequest(BaseModel):
    farmer_phone: str = Field(..., description="Farmer's phone number")
    crop_name: str = Field(..., description="Crop name")
    quantity: float = Field(..., description="Quantity")
    unit: str = Field("kg")
    price_per_unit: float = Field(..., description="Price per unit in INR")
    location: str = Field("")
    description: str = Field("")

@app.post("/api/voice-tools/list-crop")
async def list_crop(req: ListCropRequest):
    CROP_MAP_HI = {"गेहूं": "wheat", "चावल": "rice", "मक्का": "maize", "कपास": "cotton", "आलू": "potato", "टमाटर": "tomato", "प्याज": "onion"}
    crop_en = CROP_MAP_HI.get(req.crop_name.strip(), req.crop_name.strip().lower())
    VEGETABLES = ["tomato", "onion", "potato", "brinjal", "chilli", "spinach"]
    GRAINS = ["wheat", "rice", "maize", "millet", "barley"]
    category = "Vegetables" if crop_en in VEGETABLES else "Grains" if crop_en in GRAINS else "Other"
    
    farmer_id = _resolve_farmer_id(req.farmer_phone)
    
    doc_id = _firestore_add("crops", {
        "farmer_id": farmer_id,
        "name": crop_en,
        "category": category,
        "quantity": req.quantity,
        "unit": req.unit,
        "price": req.price_per_unit,
        "location": req.location or "India",
        "description": req.description,
        "status": "Ready",
        "listed_via": "voice_call",
    })
    
    if doc_id:
        return {"success": True, "crop": crop_en, "quantity": req.quantity, "unit": req.unit, "price": req.price_per_unit, "message_hi": f"बढ़िया! {crop_en} {req.quantity} {req.unit} {req.price_per_unit} रुपये में लिस्ट हो गया।"}
    return {"error": "Failed to list crop", "success": False}


# ─── Tool 5: Get My Crops ───────────────────────────────────────

@app.get("/api/voice-tools/my-crops")
async def get_my_crops(phone: str = Query(...)):
    farmer_id = _resolve_farmer_id(phone)
    result = _firestore_query("crops", "farmer_id", "EQUAL", farmer_id, limit=10)
    crops = _parse_firestore_docs(result)
    items = [f"{c.get('name', '?')} {c.get('quantity', '?')} {c.get('unit', '?')} {c.get('price', '?')} रुपये" for c in crops[:5]]
    return {
        "crops": [{"id": c["id"], "name": c.get("name"), "quantity": c.get("quantity"), "unit": c.get("unit"), "price": c.get("price"), "status": c.get("status")} for c in crops],
        "count": len(crops),
        "message_hi": f"आपकी {len(crops)} फसलें लिस्ट हैं: {', '.join(items)}" if crops else "कोई फसल लिस्ट नहीं है।",
    }


# ─── Tool 6: Get My Orders ──────────────────────────────────────

@app.get("/api/voice-tools/my-orders")
async def get_my_orders(phone: str = Query(...)):
    farmer_id = _resolve_farmer_id(phone)
    result = _firestore_query("orders", "farmer_id", "EQUAL", farmer_id, limit=10)
    orders = _parse_firestore_docs(result)
    pending = sum(1 for o in orders if o.get("status") == "Pending")
    return {
        "orders": [{"id": o["id"], "crop_name": o.get("crop_name"), "quantity": o.get("quantity"), "total_price": o.get("total_price"), "status": o.get("status")} for o in orders],
        "count": len(orders), "pending": pending,
        "message_hi": f"कुल {len(orders)} ऑर्डर हैं। {pending} नए हैं।" if orders else "कोई ऑर्डर नहीं है।",
    }


# ─── Tool 7: Update Order ───────────────────────────────────────

@app.post("/api/voice-tools/update-order")
async def update_order(request: Request):
    try:
        body = await request.json()
        order_id = body.get("order_id")
        action = body.get("action")
        STATUS_MAP = {"accept": "Processing", "reject": "Rejected", "deliver": "Delivered"}
        new_status = STATUS_MAP.get(action)
        if not new_status:
            return {"error": f"Invalid action: {action}"}
        
        _firestore_update("orders", order_id, {"status": new_status})
        return {"success": True, "order_id": order_id, "new_status": new_status, "message_hi": f"ऑर्डर की स्थिति '{new_status}' है।"}
    except Exception as e:
        return {"error": str(e), "success": False}


# ─── Tool 8: Get Profile ────────────────────────────────────────

@app.get("/api/voice-tools/profile")
async def get_profile(phone: str = Query(...)):
    farmer_id = _resolve_farmer_id(phone)
    doc = _firestore_get("profiles", farmer_id)
    if doc:
        d = _parse_firestore_doc(doc)
        return {"name": d.get("name"), "role": d.get("role"), "phone": d.get("phone"), "message_hi": f"नमस्ते {d.get('name', 'किसान जी')}!"}
    return {"name": "Farmer", "role": "farmer", "message_hi": "नमस्ते किसान जी!"}


# ─── Tool 9: Search Products ────────────────────────────────────

@app.get("/api/voice-tools/search")
async def search_products(query: str = Query(""), limit: int = Query(5)):
    result = _firestore_query("crops", "status", "EQUAL", "Ready", limit=20)
    docs = _parse_firestore_docs(result)
    results = []
    for d in docs:
        name = d.get("name", "")
        if not query or query.lower() in name.lower():
            results.append({"id": d["id"], "name": name, "price": d.get("price"), "unit": d.get("unit"), "quantity": d.get("quantity"), "location": d.get("location")})
        if len(results) >= limit:
            break
    return {"products": results, "count": len(results)}


# ─── Tool 10: Link Phone ────────────────────────────────────────

class LinkPhoneRequest(BaseModel):
    firebase_uid: str = Field(..., description="Firebase Auth UID")
    phone: str = Field(..., description="Phone number to link")

@app.post("/api/voice-tools/link-phone")
async def link_phone(req: LinkPhoneRequest):
    phone = req.phone.strip()
    if not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0")
    
    _firestore_set("phone_lookup", phone, {"firebase_uid": req.firebase_uid, "phone": phone})
    _firestore_update("profiles", req.firebase_uid, {"phone": phone})
    
    return {
        "success": True, "phone": phone,
        "message": f"Phone {phone} linked to your account.",
        "message_hi": f"{phone} आपके खाते से जुड़ गया। अब फ़ोन कॉल पर फसलें और ऑर्डर देख सकते हैं।",
    }


@app.get("/api/voice-tools/resolve-phone")
async def resolve_phone(phone: str = Query(...)):
    uid = _resolve_farmer_id(phone)
    is_linked = uid != phone and not phone.startswith("+91" + uid)
    return {"phone": phone, "firebase_uid": uid if is_linked else None, "is_linked": is_linked}


# ─── Health ──────────────────────────────────────────────────────

@app.get("/api/voice-tools/health")
async def health():
    return {"status": "ok", "tools": 11, "firebase_project": FIREBASE_PROJECT}
