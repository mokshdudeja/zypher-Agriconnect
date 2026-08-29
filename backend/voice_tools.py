"""
AgriConnect — Voice Agent API Tools

These endpoints are called by the Sarvam Voice Agent as "API tools"
during phone conversations with farmers. The agent decides which
tool to call based on what the farmer says.

Tools available to the agent:
1. get_crop_price     — fetch price prediction for any crop/state
2. get_weather        — 7-day weather forecast with farming alerts
3. get_crop_recommend — soil/climate-based crop suggestions
4. list_crop          — add a new crop listing (voice → Firestore)
5. get_my_crops       — list all crops the farmer has listed
6. get_my_orders      — list orders for this farmer
7. update_order       — accept/reject/deliver an order
8. get_profile        — farmer's profile info
9. search_products    — find products available for purchase

Docs: https://docs.sarvam.ai/conversations/build/tools/https-tool.md
"""

import os
import json
import logging
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


# ─── Tool 1: Crop Price Prediction ──────────────────────────────

@app.get("/api/voice-tools/price")
async def get_crop_price(
    crop: str = Query(..., description="Crop name in English or Hindi (e.g. wheat, गेहूं, rice, चावल)"),
    state: str = Query("uttar_pradesh", description="Indian state in snake_case"),
    unit: str = Query("kg", description="Price unit: kg, quintal, or tonne"),
):
    """
    Get current and predicted crop prices for 7/15/30 days.
    
    Example: GET /api/voice-tools/price?crop=wheat&state=punjab&unit=kg
    Returns: current price, predictions, trend, factors
    """
    # Hindi/romanized crop name mapping
    CROP_MAP = {
        "गेहूं": "wheat", "गेहूँ": "wheat", "gehun": "wheat", "gehu": "wheat",
        "चावल": "rice", "chawal": "rice", "dhaan": "rice",
        "मक्का": "maize", "makka": "maize", "corn": "maize",
        "कपास": "cotton", "kapas": "cotton",
        "सोयाबीन": "soybean", "soybean": "soybean",
        "आलू": "potato", "aloo": "potato",
        "टमाटर": "tomato", "tamatar": "tomato",
        "प्याज": "onion", "pyaz": "onion", "pyaaz": "onion",
        "मूंगफली": "groundnut", "moongfali": "groundnut",
        "गन्ना": "sugarcane", "ganna": "sugarcane",
        "मूंग": "moong", "moong": "moong",
        "सरसों": "mustard", "sarson": "mustard",
        "चना": "chickpea", "chana": "chickpea",
        "सूरजमुखी": "sunflower", "surajmukhi": "sunflower",
    }
    
    # Hindi state mapping
    STATE_MAP = {
        "उत्तर प्रदेश": "uttar_pradesh", "UP": "uttar_pradesh",
        "महाराष्ट्र": "maharashtra",
        "पंजाब": "punjab",
        "हरियाणा": "haryana",
        "मध्य प्रदेश": "madhya_pradesh", "MP": "madhya_pradesh",
        "राजस्थान": "rajasthan",
        "कर्नाटक": "karnataka",
        "तमिल नाडु": "tamil_nadu", "TN": "tamil_nadu",
        "आंध्र प्रदेश": "andhra_pradesh", "AP": "andhra_pradesh",
        "गुजरात": "gujarat",
        "पश्चिम बंगाल": "west_bengal", "WB": "west_bengal",
        "बिहार": "bihar",
    }
    
    crop_slug = CROP_MAP.get(crop.strip(), crop.strip().lower().replace(" ", "_"))
    state_slug = STATE_MAP.get(state.strip(), state.strip().lower().replace(" ", "_"))
    
    try:
        resp = requests.get(
            f"{API_BASE}/api/predict/{crop_slug}/{state_slug}",
            params={"unit": unit, "use_cache": "false"},
            timeout=15,
        )
        data = resp.json()
        
        if "detail" in data:
            return {"error": data["detail"], "crop": crop, "state": state}
        
        # Build farmer-friendly Hindi response
        crop_hi = {v: k for k, v in CROP_MAP.items()}.get(crop_slug, crop)
        return {
            "crop": crop_slug,
            "crop_hindi": crop_hi,
            "state": state_slug,
            "current_price": data.get("current_price"),
            "predicted_7d": data.get("predicted_price_7d"),
            "predicted_15d": data.get("predicted_price_15d"),
            "predicted_30d": data.get("predicted_price_30d"),
            "unit": data.get("unit", unit),
            "trend": data.get("trend"),
            "factors": data.get("factors", []),
            "confidence": data.get("confidence"),
            "message_hi": _price_message_hi(crop_slug, data, unit),
        }
    except Exception as e:
        logger.error(f"Price tool error: {e}")
        return {"error": str(e)}


def _price_message_hi(crop: str, data: dict, unit: str) -> str:
    """Generate Hindi price summary for TTS."""
    cur = data.get("current_price", 0)
    p7 = data.get("predicted_price_7d", 0)
    trend = data.get("trend", "stable")
    trend_hi = {"bullish": "बढ़ रही है", "bearish": "घट रही है", "stable": "स्थिर है"}
    return f"{crop} की आज की कीमत {cur} रुपये प्रति {unit} है। 7 दिन में {p7} रुपये होने की संभावना है। भाव {trend_hi.get(trend, 'स्थिर है')}।"


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
    "karnataka": "कर्नाटक", "tamil_nadu": "तमिल नाडु", "andhra_pradesh": "आंध्र प्रदेश",
    "gujarat": "गुजरात", "west_bengal": "पश्चिम बंगाल", "bihar": "बिहार",
}


@app.get("/api/voice-tools/weather")
async def get_weather(
    state: str = Query(..., description="Indian state"),
    days: int = Query(3, description="Forecast days (1-7)"),
):
    """
    Get weather forecast with farming-specific alerts.
    
    Returns: temperature, rainfall, humidity, alerts, farming advice in Hindi.
    """
    coords = STATE_COORDS.get(state.strip().lower().replace(" ", "_"))
    if not coords:
        return {"error": f"Unknown state: {state}. Supported: {list(STATE_COORDS.keys())}"}
    
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords[0], "longitude": coords[1],
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_max,wind_speed_10m_max",
                "current": "temperature_2m,relative_humidity_2m,weather_code",
                "timezone": "Asia/Kolkata",
                "forecast_days": min(days, 7),
            },
            timeout=10,
        )
        data = resp.json()
        daily = data.get("daily", {})
        current = data.get("current", {})
        
        # Generate farming alerts
        alerts = []
        farming_tips = []
        
        for i in range(len(daily.get("time", []))):
            tmax = daily["temperature_2m_max"][i]
            rain = daily["precipitation_sum"][i]
            wind = daily.get("wind_speed_10m_max", [0])[i] if i < len(daily.get("wind_speed_10m_max", [])) else 0
            
            if tmax > 42:
                alerts.append({"day": daily["time"][i], "type": "heatwave", "message": f"तापमान {tmax}°C — गर्मी की लहर!", "severity": "high"})
                farming_tips.append("फसलों को सुबह जल्दी सींचें। दोपहर में छाया में रखें।")
            elif tmax > 38:
                alerts.append({"day": daily["time"][i], "type": "hot", "message": f"तापमान {tmax}°C — गर्म दिन", "severity": "medium"})
            
            if rain > 50:
                alerts.append({"day": daily["time"][i], "type": "heavy_rain", "message": f"भारी बारिश {rain}mm!", "severity": "high"})
                farming_tips.append("बारिश से पहले फसल की कटाई कर लें। जल निकासी की व्यवस्था करें।")
            elif rain > 20:
                farming_tips.append("बारिश के बाद खाद डालना फायदेमंद होगा।")
            
            if tmax < 5:
                alerts.append({"day": daily["time"][i], "type": "frost", "message": f"पाला पड़ सकता है! तापमान {tmax}°C", "severity": "high"})
                farming_tips.append("संवेदनशील फसलों को ढकें। सिंचाई करें — पानी से तापमान बचाव होता है।")
        
        if not farming_tips:
            farming_tips.append("मौसम अनुकूल है। नियमित सिंचाई जारी रखें।")
        
        state_hi = STATE_MAP_HI.get(state, state)
        
        return {
            "state": state,
            "state_hindi": state_hi,
            "current_temp": current.get("temperature_2m"),
            "current_humidity": current.get("relative_humidity_2m"),
            "forecast": [
                {
                    "date": daily["time"][i],
                    "temp_max": daily["temperature_2m_max"][i],
                    "temp_min": daily["temperature_2m_min"][i],
                    "rain_mm": daily["precipitation_sum"][i],
                }
                for i in range(len(daily.get("time", [])))
            ],
            "alerts": alerts,
            "farming_tips": list(set(farming_tips)),
            "message_hi": _weather_message_hi(state_hi, current, daily, alerts),
        }
    except Exception as e:
        return {"error": str(e)}


def _weather_message_hi(state: str, current: dict, daily: dict, alerts: list) -> str:
    temp = current.get("temperature_2m", "?")
    hum = current.get("relative_humidity_2m", "?")
    msg = f"{state} में अभी तापमान {temp}°C और नमी {hum}% है।"
    if alerts:
        msg += f" {len(alerts)} मौसम अलर्ट हैं।"
    else:
        msg += " मौसम सामान्य है।"
    return msg


# ─── Tool 3: Crop Recommendation ────────────────────────────────

@app.get("/api/voice-tools/recommend")
async def get_crop_recommend(
    state: str = Query("uttar_pradesh"),
    soil_type: str = Query("loamy", description="loamy, clayey, sandy, black, red"),
    ph: float = Query(6.5),
    temperature: int = Query(25),
    rainfall: int = Query(800),
    season: str = Query("rabi", description="rabi, kharif, zaid"),
):
    """
    Get top crop recommendations based on soil, climate, and season.
    """
    try:
        resp = requests.post(
            f"{API_BASE}/api/crop-recommend",
            json={
                "soil_type": soil_type, "ph": ph, "nitrogen": 40,
                "phosphorus": 30, "potassium": 35, "rainfall": rainfall,
                "temperature": temperature, "season": season,
            },
            timeout=15,
        )
        data = resp.json()
        recs = data.get("recommendations", [])[:3]
        
        return {
            "recommendations": [
                {"crop": r["crop"], "score": r["suitability_score"], "yield": r.get("estimated_yield_qha"), "price": r.get("estimated_price_per_quintal")}
                for r in recs
            ],
            "message_hi": _recommend_message_hi(recs),
        }
    except Exception as e:
        return {"error": str(e)}


def _recommend_message_hi(recs: list) -> str:
    if not recs:
        return "इस मिट्टी और मौसम के लिए कोई सुझाव नहीं मिला।"
    names = " और ".join([r["crop"] for r in recs[:3]])
    return f"आपकी मिट्टी और मौसम के लिए {names} उगाना सबसे अच्छा रहेगा।"


# ─── Tool 4: List Crop (Voice → Firestore) ──────────────────────

class ListCropRequest(BaseModel):
    farmer_phone: str = Field(..., description="Farmer's phone number (used as ID)")
    crop_name: str = Field(..., description="Crop name in English or Hindi")
    quantity: float = Field(..., description="Quantity available")
    unit: str = Field("kg", description="kg, quintal, or ton")
    price_per_unit: float = Field(..., description="Price per unit in INR")
    location: str = Field("", description="Location/city")
    description: str = Field("", description="Additional details")


@app.post("/api/voice-tools/list-crop")
async def list_crop(req: ListCropRequest):
    """
    List a new crop for sale. The farmer speaks, the agent extracts details,
    and calls this tool to save to Firestore.
    """
    CROP_MAP_HI = {
        "गेहूं": "wheat", "चावल": "rice", "मक्का": "maize", "कपास": "cotton",
        "सोयाबीन": "soybean", "आलू": "potato", "टमाटर": "tomato",
        "प्याज": "onion", "मूंगफली": "groundnut", "गन्ना": "sugarcane",
    }
    
    crop_en = CROP_MAP_HI.get(req.crop_name.strip(), req.crop_name.strip().lower())
    
    # Determine category
    VEGETABLES = ["tomato", "onion", "potato", "brinjal", "chilli", "spinach"]
    GRAINS = ["wheat", "rice", "maize", "millet", "barley"]
    category = "Vegetables" if crop_en in VEGETABLES else "Grains" if crop_en in GRAINS else "Other"
    
    # Use prediction API to validate price
    predicted_price = None
    try:
        price_resp = requests.get(
            f"{API_BASE}/api/predict/{crop_en}/uttar_pradesh",
            params={"unit": req.unit, "use_cache": "true"},
            timeout=10,
        )
        price_data = price_resp.json()
        predicted_price = price_data.get("current_price")
    except:
        pass
    
    # Write to Firestore via Firebase Admin SDK
    try:
        import firebase_admin
        from firebase_admin import firestore
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        
        db = firestore.client()
        
        doc_ref = db.collection("crops").add({
            "farmer_id": req.farmer_phone,  # Use phone as ID
            "name": crop_en,
            "category": category,
            "quantity": req.quantity,
            "unit": req.unit,
            "price": req.price_per_unit,
            "location": req.location or "India",
            "description": req.description,
            "status": "Ready",
            "created_at": firestore.SERVER_TIMESTAMP,
            "listed_via": "voice_call",
        })
        
        return {
            "success": True,
            "crop": crop_en,
            "quantity": req.quantity,
            "unit": req.unit,
            "price": req.price_per_unit,
            "predicted_market_price": predicted_price,
            "message_hi": f"बढ़िया! {crop_en} {req.quantity} {req.unit} {req.price_per_unit} रुपये प्रति {req.unit} में लिस्ट हो गया। {'बाजार भाव ' + str(predicted_price) + ' रुपये है।' if predicted_price else ''}",
        }
    except Exception as e:
        logger.error(f"List crop error: {e}")
        return {"error": f"Failed to list crop: {str(e)}", "success": False}


# ─── Tool 5: Get My Crops ───────────────────────────────────────

@app.get("/api/voice-tools/my-crops")
async def get_my_crops(
    phone: str = Query(..., description="Farmer's phone number"),
):
    """Get all crops listed by this farmer."""
    try:
        import firebase_admin
        from firebase_admin import firestore
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        
        db = firestore.client()
        docs = db.collection("crops").where("farmer_id", "==", phone).order_by("created_at", direction=firestore.Query.DESCENDING).limit(10).stream()
        
        crops = []
        for doc in docs:
            d = doc.to_dict()
            crops.append({
                "id": doc.id,
                "name": d.get("name"),
                "quantity": d.get("quantity"),
                "unit": d.get("unit"),
                "price": d.get("price"),
                "status": d.get("status"),
                "location": d.get("location"),
            })
        
        return {
            "crops": crops,
            "count": len(crops),
            "message_hi": _my_crops_message_hi(crops),
        }
    except Exception as e:
        return {"error": str(e), "crops": []}


def _my_crops_message_hi(crops: list) -> str:
    if not crops:
        return "आपने अभी तक कोई फसल लिस्ट नहीं की है। 'नई फसल जोड़ें' बोलें।"
    items = [f"{c['name']} {c['quantity']} {c['unit']} {c['price']} रुपये" for c in crops[:5]]
    return f"आपकी {len(crops)} फसलें लिस्ट हैं: {', '.join(items)}"


# ─── Tool 6: Get My Orders ──────────────────────────────────────

@app.get("/api/voice-tools/my-orders")
async def get_my_orders(
    phone: str = Query(..., description="Farmer's phone number"),
):
    """Get orders for this farmer."""
    try:
        import firebase_admin
        from firebase_admin import firestore
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        
        db = firestore.client()
        docs = db.collection("orders").where("farmer_id", "==", phone).order_by("created_at", direction=firestore.Query.DESCENDING).limit(10).stream()
        
        orders = []
        for doc in docs:
            d = doc.to_dict()
            orders.append({
                "id": doc.id,
                "crop_name": d.get("crop_name"),
                "quantity": d.get("quantity"),
                "unit": d.get("unit"),
                "total_price": d.get("total_price"),
                "status": d.get("status"),
                "buyer": d.get("wholesaler_name") or d.get("consumer_name") or "Buyer",
            })
        
        return {
            "orders": orders,
            "count": len(orders),
            "pending": sum(1 for o in orders if o["status"] == "Pending"),
            "message_hi": _my_orders_message_hi(orders),
        }
    except Exception as e:
        return {"error": str(e), "orders": []}


def _my_orders_message_hi(orders: list) -> str:
    if not orders:
        return "कोई ऑर्डर नहीं है।"
    pending = [o for o in orders if o["status"] == "Pending"]
    msg = f"कुल {len(orders)} ऑर्डर हैं।"
    if pending:
        msg += f" {len(pending)} नए ऑर्डर हैं जिनका इंतजार है।"
    return msg


# ─── Tool 7: Update Order ───────────────────────────────────────

@app.post("/api/voice-tools/update-order")
async def update_order(request: Request):
    """
    Accept, reject, or mark order as delivered.
    
    Body: {"order_id": "xxx", "action": "accept|reject|deliver", "farmer_phone": "+91..."}
    """
    try:
        body = await request.json()
        order_id = body.get("order_id")
        action = body.get("action")
        farmer_phone = body.get("farmer_phone")
        
        STATUS_MAP = {
            "accept": "Processing",
            "reject": "Rejected",
            "deliver": "Delivered",
        }
        
        new_status = STATUS_MAP.get(action)
        if not new_status:
            return {"error": f"Invalid action: {action}. Use accept, reject, or deliver."}
        
        import firebase_admin
        from firebase_admin import firestore
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        
        db = firestore.client()
        db.collection("orders").document(order_id).update({"status": new_status})
        
        return {
            "success": True,
            "order_id": order_id,
            "new_status": new_status,
            "message_hi": f"ऑर्डर {order_id[:8]}... की स्थिति अब '{new_status}' है।",
        }
    except Exception as e:
        return {"error": str(e), "success": False}


# ─── Tool 8: Get Profile ────────────────────────────────────────

@app.get("/api/voice-tools/profile")
async def get_profile(
    phone: str = Query(..., description="Farmer's phone number"),
):
    """Get farmer's profile info."""
    try:
        import firebase_admin
        from firebase_admin import firestore
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        
        db = firestore.client()
        doc = db.collection("profiles").document(phone).get()
        
        if doc.exists:
            d = doc.to_dict()
            return {
                "name": d.get("name"),
                "role": d.get("role"),
                "phone": d.get("phone"),
                "created_at": str(d.get("created_at", "")),
                "message_hi": f"नमस्ते {d.get('name', 'किसान जी')}! आप {d.get('role', 'farmer')} हैं।",
            }
        else:
            return {"name": "Farmer", "role": "farmer", "message_hi": "नमस्ते किसान जी!"}
    except Exception as e:
        return {"error": str(e)}


# ─── Tool 9: Search Products ────────────────────────────────────

@app.get("/api/voice-tools/search")
async def search_products(
    query: str = Query("", description="Search term (crop name)"),
    limit: int = Query(5),
):
    """Search available products/crops."""
    try:
        import firebase_admin
        from firebase_admin import firestore
        
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        
        db = firestore.client()
        
        if query:
            docs = db.collection("crops").where("status", "==", "Ready").limit(20).stream()
        else:
            docs = db.collection("crops").where("status", "==", "Ready").limit(limit).stream()
        
        results = []
        for doc in docs:
            d = doc.to_dict()
            name = d.get("name", "")
            if not query or query.lower() in name.lower():
                results.append({
                    "id": doc.id,
                    "name": name,
                    "price": d.get("price"),
                    "unit": d.get("unit"),
                    "quantity": d.get("quantity"),
                    "location": d.get("location"),
                })
            if len(results) >= limit:
                break
        
        return {"products": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e), "products": []}


# ─── Health ──────────────────────────────────────────────────────

@app.get("/api/voice-tools/health")
async def health():
    return {"status": "ok", "tools": 9}
