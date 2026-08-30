"""
AgriConnect — Firestore Demo Data Seeder
=========================================
Seeds realistic Indian agriculture data for hackathon demo.
Creates farmer accounts, crop listings, and order history.

Usage:
    cd backend
    python seed_demo.py
"""

import json
import random
import hashlib
from datetime import datetime, timedelta

import requests

# ─── Firebase Config ────────────────────────────────────────────
PROJECT = "agriconnect-zypher-db"
API_KEY = "AIzaSyCPqo6OEr8UwJV1RXce0It-ZR2Fjjz_WIo"
BASE = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
FIRESTORE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"


def get_token(email, password):
    """Get Firebase Auth ID token."""
    resp = requests.post(BASE, json={"email": email, "password": password, "returnSecureToken": True})
    data = resp.json()
    if "idToken" not in data:
        print(f"  Auth failed for {email}: {data.get('error', {}).get('message', 'unknown')}")
        return None
    return data["idToken"]


def create_user(email, password, name, role):
    """Create a new Firebase Auth user."""
    resp = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}",
        json={"email": email, "password": password, "returnSecureToken": True}
    )
    data = resp.json()
    if "idToken" in data:
        uid = data["localId"]
        print(f"  Created user: {email} (uid: {uid[:12]}...)")
        return uid
    else:
        # User might already exist, try to sign in
        resp2 = requests.post(BASE, json={"email": email, "password": password, "returnSecureToken": True})
        data2 = resp2.json()
        if "idToken" in data2:
            uid = data2["localId"]
            print(f"  User already exists: {email} (uid: {uid[:12]}...)")
            return uid
        print(f"  Failed to create {email}: {data.get('error', {}).get('message', '')}")
        return None


def write_doc(token, collection, doc_id, data):
    """Write a document to Firestore."""
    url = f"{FIRESTORE}/{collection}/{doc_id}"
    resp = requests.patch(url, json={"fields": {k: to_firestore_value(v) for k, v in data.items()}},
                          headers={"Authorization": f"Bearer {token}"})
    if resp.status_code in [200, 201]:
        return True
    print(f"    Write failed: {collection}/{doc_id} -> {resp.status_code}")
    return False


def to_firestore_value(v):
    """Convert Python value to Firestore REST API format."""
    if isinstance(v, bool):
        return {"booleanValue": v}
    elif isinstance(v, int):
        return {"integerValue": str(v)}
    elif isinstance(v, float):
        return {"doubleValue": v}
    elif isinstance(v, str):
        return {"stringValue": v}
    elif isinstance(v, list):
        return {"arrayValue": {"values": [to_firestore_value(i) for i in v]}}
    elif isinstance(v, dict):
        return {"mapValue": {"fields": {k: to_firestore_value(vv) for k, vv in v.items()}}}
    else:
        return {"stringValue": str(v)}


def main():
    print("\n" + "=" * 60)
    print("  AgriConnect — Firestore Demo Data Seeder")
    print("=" * 60)

    # Login as admin to get token
    admin_token = get_token("admin@agriconnect.com", "admin@agriconnect")
    if not admin_token:
        print("Failed to authenticate as admin!")
        return

    # ─── 1. Create additional farmer accounts ────────────────────
    print("\n[1/4] Creating farmer accounts...")

    extra_farmers = [
        ("rahul@agriconnect.com", "rahul123", "Rahul Kumar", "farmer", "9876543210", "Ludhiana, Punjab"),
        ("sunita@agriconnect.com", "sunita123", "Sunita Devi", "farmer", "9876543211", "Meerut, Uttar Pradesh"),
    ]

    farmer_uids = {
        "9CjjXUMzBCUk": {"name": "Ram Singh Farmer", "phone": "9876543200", "location": "Ludhiana, Punjab"},
    }

    for email, pw, name, role, phone, location in extra_farmers:
        uid = create_user(email, pw, name, role)
        if uid:
            # Create profile
            write_doc(admin_token, "profiles", uid, {
                "name": name,
                "role": role,
                "phone": phone,
                "avatar": "👨‍🌾",
                "created_at": datetime.now().isoformat(),
                "location": location,
            })
            farmer_uids[uid[:12]] = {"name": name, "phone": phone, "location": location}

    # ─── 2. Seed crop listings ────────────────────────────────────
    print("\n[2/4] Seeding crop listings...")

    # Realistic Indian agriculture crops with prices in Rs/kg
    crops_data = [
        # Ram Singh's crops (Punjab — wheat belt)
        {"farmer_uid": "9CjjXUMzBCUk", "farmer_name": "Ram Singh Farmer",
         "crops": [
            {"name": "wheat", "category": "Grains", "qty": 50, "unit": "quintal", "price": 2200, "location": "Ludhiana, Punjab", "harvest_days_ago": 5},
            {"name": "rice", "category": "Grains", "qty": 30, "unit": "quintal", "price": 2600, "location": "Ludhiana, Punjab", "harvest_days_ago": 3},
            {"name": "mustard", "category": "Spices", "qty": 10, "unit": "quintal", "price": 5200, "location": "Ludhiana, Punjab", "harvest_days_ago": 7},
        ]},
        # Rahul's crops (Punjab — mixed farming)
        {"farmer_uid_key": "rahul@agriconnect.com", "farmer_name": "Rahul Kumar",
         "crops": [
            {"name": "maize", "category": "Grains", "qty": 40, "unit": "quintal", "price": 1900, "location": "Jalandhar, Punjab", "harvest_days_ago": 2},
            {"name": "potato", "category": "Vegetables", "qty": 20, "unit": "quintal", "price": 1600, "location": "Jalandhar, Punjab", "harvest_days_ago": 1},
            {"name": "onion", "category": "Vegetables", "qty": 15, "unit": "quintal", "price": 1800, "location": "Jalandhar, Punjab", "harvest_days_ago": 4},
        ]},
        # Sunita's crops (UP — sugarcane + grains)
        {"farmer_uid_key": "sunita@agriconnect.com", "farmer_name": "Sunita Devi",
         "crops": [
            {"name": "sugarcane", "category": "Grains", "qty": 100, "unit": "quintal", "price": 2850, "location": "Meerut, UP", "harvest_days_ago": 1},
            {"name": "wheat", "category": "Grains", "qty": 25, "unit": "quintal", "price": 2150, "location": "Meerut, UP", "harvest_days_ago": 6},
        ]},
    ]

    crop_ids = []
    for farmer_group in crops_data:
        farmer_uid = farmer_group.get("farmer_uid", "")
        # Look up UID from email-based key
        if "farmer_uid_key" in farmer_group:
            # We need to look up the UID — use a known mapping
            # For simplicity, we'll use the profile name to find it
            farmer_uid = None
            for uid_prefix, info in farmer_uids.items():
                if info["name"] == farmer_group["farmer_name"]:
                    farmer_uid = uid_prefix
                    break
            if not farmer_uid:
                print(f"    Could not find UID for {farmer_group['farmer_name']}")
                continue

        for crop in farmer_group["crops"]:
            # Generate a deterministic doc ID
            doc_id = hashlib.md5(f"{farmer_uid}{crop['name']}{crop['location']}".encode()).hexdigest()[:20]

            # Calculate harvest date
            harvest_date = (datetime.now() - timedelta(days=crop["harvest_days_ago"])).strftime("%Y-%m-%d")

            # Slight price variation per crop
            actual_price = crop["price"] + random.randint(-50, 50)

            data = {
                "farmer_id": farmer_uid,
                "name": crop["name"],
                "category": crop["category"],
                "quantity": crop["qty"],
                "unit": crop["unit"],
                "price": actual_price,
                "harvest_date": harvest_date,
                "description": f"Fresh {crop['name']} harvested from {crop['location']}. Premium quality.",
                "location": crop["location"],
                "status": "Ready",
                "created_at": (datetime.now() - timedelta(days=crop["harvest_days_ago"])).isoformat(),
            }

            success = write_doc(admin_token, "crops", doc_id, data)
            if success:
                print(f"    {crop['name']:12s} {crop['qty']:>3} {crop['unit']:<8s} Rs{actual_price:>5}/unit — {crop['location']}")
                crop_ids.append({"id": doc_id, **crop, "farmer_id": farmer_uid, "price": actual_price})

    # ─── 3. Seed orders ──────────────────────────────────────────
    print("\n[3/4] Seeding orders...")

    # Get wholesaler UID
    wholesaler_resp = requests.post(BASE, json={"email": "wholesaler@agriconnect.com", "password": "wholesaler@agriconnect", "returnSecureToken": True})
    wholesaler_uid = wholesaler_resp.json().get("localId", "")

    # Create realistic orders
    orders = [
        # Wholesaler bought wheat from Ram Singh
        {
            "crop_name": "wheat",
            "farmer_id": crop_ids[0]["farmer_id"] if crop_ids else "9CjjXUMzBCUk",
            "farmer_name": "Ram Singh Farmer",
            "wholesaler_id": wholesaler_uid,
            "wholesaler_name": "Shyam Trading Co",
            "quantity": 20,
            "unit": "quintal",
            "price_per_unit": 2200,
            "total_price": 44000,
            "status": "Delivered",
            "days_ago": 10,
        },
        # Wholesaler bought rice from Ram Singh
        {
            "crop_name": "rice",
            "farmer_id": crop_ids[0]["farmer_id"] if crop_ids else "9CjjXUMzBCUk",
            "farmer_name": "Ram Singh Farmer",
            "wholesaler_id": wholesaler_uid,
            "wholesaler_name": "Shyam Trading Co",
            "quantity": 15,
            "unit": "quintal",
            "price_per_unit": 2600,
            "total_price": 39000,
            "status": "Delivered",
            "days_ago": 5,
        },
        # Wholesaler bought maize from Rahul
        {
            "crop_name": "maize",
            "farmer_id": crop_ids[3]["farmer_id"] if len(crop_ids) > 3 else "",
            "farmer_name": "Rahul Kumar",
            "wholesaler_id": wholesaler_uid,
            "wholesaler_name": "Shyam Trading Co",
            "quantity": 25,
            "unit": "quintal",
            "price_per_unit": 1900,
            "total_price": 47500,
            "status": "Pending",
            "days_ago": 1,
        },
        # Consumer bought potato
        {
            "crop_name": "potato",
            "farmer_id": crop_ids[4]["farmer_id"] if len(crop_ids) > 4 else "",
            "farmer_name": "Rahul Kumar",
            "wholesaler_id": "HJtVBo0TNMc2",  # consumer uid
            "wholesaler_name": "Priya Sharma",
            "quantity": 5,
            "unit": "quintal",
            "price_per_unit": 1600,
            "total_price": 8000,
            "status": "Processing",
            "days_ago": 2,
        },
    ]

    for i, order in enumerate(orders):
        if not order["farmer_id"]:
            continue
        order_hash = f"{order['crop_name']}{order['wholesaler_id']}{i}"
        order_id = f"order-{hashlib.md5(order_hash.encode()).hexdigest()[:12]}"
        created = (datetime.now() - timedelta(days=order["days_ago"])).isoformat()

        data = {
            "crop_name": order["crop_name"],
            "farmer_id": order["farmer_id"],
            "farmer_name": order["farmer_name"],
            "wholesaler_id": order["wholesaler_id"],
            "wholesaler_name": order["wholesaler_name"],
            "quantity": order["quantity"],
            "unit": order["unit"],
            "price_per_unit": order["price_per_unit"],
            "total_price": order["total_price"],
            "status": order["status"],
            "created_at": created,
        }

        success = write_doc(admin_token, "orders", order_id, data)
        if success:
            print(f"    {order['crop_name']:12s} {order['quantity']:>2} {order['unit']:<8s} Rs{order['total_price']:>6} — {order['status']}")

    # ─── 4. Summary ──────────────────────────────────────────────
    print("\n[4/4] Summary")
    print(f"\n  Farmers:     {len(farmer_uids)} accounts (Ram Singh, Rahul Kumar, Sunita Devi)")
    print(f"  Crops:       {len(crop_ids)} listings across wheat, rice, maize, mustard, potato, onion, sugarcane")
    print(f"  Orders:      {len(orders)} orders (Delivered: 2, Processing: 1, Pending: 1)")
    print(f"  Wholesaler:  Shyam Trading Co (BojdAc6nmyR9)")
    print(f"  Consumer:    Priya Sharma (HJtVBo0TNMc2)")
    print(f"\n  Demo Accounts:")
    print(f"    admin@agriconnect.com    / admin@agriconnect    (Admin)")
    print(f"    farmer@agriconnect.com   / farmer@agriconnect   (Farmer: Ram Singh)")
    print(f"    rahul@agriconnect.com    / rahul123             (Farmer: Rahul Kumar)")
    print(f"    sunita@agriconnect.com   / sunita123            (Farmer: Sunita Devi)")
    print(f"    wholesaler@agriconnect.com / wholesaler@agriconnect (Wholesaler)")
    print(f"    consumer@agriconnect.com / consumer@agriconnect (Consumer)")
    print("=" * 60)


if __name__ == "__main__":
    main()
