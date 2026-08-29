# 🌾 AgriConnect — AI-Powered Agricultural Platform

> **Smart India Hackathon (SIH) Project** — Connecting Farmers, Wholesalers & Consumers through AI-driven crop price predictions, voice-enabled IVR services, and a full-stack marketplace.

---

## 🎯 Problem Statement

Indian farmers face **information asymmetry** — they lack real-time crop price data, weather insights, and direct market access. Middlemen exploit this gap, leading to farmer distress and consumer inflation.

## 💡 Solution

AgriConnect is a **full-stack agricultural AI platform** that provides:

1. **AI Crop Price Prediction** — XGBoost + LSTM + Prophet ensemble forecasting 7/15/30 days ahead
2. **Voice-Enabled IVR** — Farmers call a number, speak their crop name in Hindi/English, and get price forecasts via TTS
3. **Live Weather Alerts** — Real-time weather data with farming-specific alerts (heatwave, frost, heavy rain)
4. **Direct Marketplace** — Farmers list crops, wholesalers/consumers buy directly
5. **Admin Dashboard** — Real-time analytics, user management, transaction monitoring

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USERS (Browser/Mobile)                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   CloudFront │  (Planned — pending email verification)
                    │   + S3       │  React SPA static hosting
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐      ┌─────────────────────┐
                    │  API Gateway │─────▶│   Lambda Functions   │
                    │  (REST API)  │      │                      │
                    └──────┬──────┘      │  • api_handler       │
                           │             │  • daily_update       │
                           │             │  • weekly_retrain     │
                    ┌──────▼──────┐      └─────────┬───────────┘
                    │  DynamoDB    │                │
                    │  • crop_prices│               │
                    │  • call_logs  │      ┌────────▼────────┐
                    │  • user_sessions     │    S3 Bucket     │
                    └─────────────┘      │  • Training data  │
                                         │  • Model artifacts│
                                         └──────────────────┘

    ┌──────────────────────────────────────────────────────────┐
    │                    Firebase Services                      │
    │  • Authentication (Email/Password)                       │
    │  • Firestore (Users, Crops, Orders, Real-time sync)     │
    └──────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────┐
    │              External APIs                                │
    │  • OpenMeteo — Weather data (free, no key)               │
    │  • Sarvam AI — Hindi TTS/STT (voice IVR)                │
    │  • Exotel — Phone call handling (IVR)                    │
    └──────────────────────────────────────────────────────────┘
```

---

## 🚀 Live Deployment

| Component | URL | Status |
|-----------|-----|--------|
| **Frontend** | [http://agriconnect-frontend-dev.s3-website.ap-south-1.amazonaws.com](http://agriconnect-frontend-dev.s3-website.ap-south-1.amazonaws.com) | ✅ Live |
| **Backend API** | [https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev/](https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev/) | ✅ Live |
| **Firebase Auth** | agriconnect-zypher-db.firebaseapp.com | ✅ Configured |
| **GitHub** | [github.com/mokshdudeja/zypher-Agriconnect](https://github.com/mokshdudeja/zypher-Agriconnect) | ✅ Public |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/predict/{crop}/{state}` | GET | AI price prediction (7/15/30 day) |
| `/api/weather/v2?state={state}&days={n}` | GET | Weather forecast + alerts |
| `/api/crop-recommend` | POST | Crop recommendation engine |
| `/api/ivr/incoming` | POST | IVR incoming call handler |
| `/api/ivr/gather` | POST | IVR speech processing |
| `/api/ivr/health` | GET | System health check |

---

## 🧠 AI/ML Pipeline

### Model Architecture
- **Primary:** XGBoost (feature importance + baseline predictions)
- **Secondary:** LSTM (time series patterns)
- **Final:** Ensemble (XGBoost 40% + LSTM 35% + Prophet 25%)

### Features Engineered (20+)
- Lag prices (1, 3, 7, 14, 30 days)
- Rolling averages (7-day, 14-day, 30-day)
- Price momentum and volatility
- Weather anomalies (rainfall deviation from normal)
- Seasonal encoding (Kharif/Rabi/Zaid)
- State-wise demand-supply gap

### Data Sources
- **Agmarknet.gov.in** — Historical mandi prices (2015-2025)
- **OpenMeteo API** — Weather data (temperature, rainfall, humidity)
- **DES India** — Crop production data
- **Fuel prices** — Transportation cost indicator

---

## 🛠️ Tech Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| React 19 + TypeScript | UI framework |
| Vite 8 | Build tool |
| Tailwind CSS 4 | Styling |
| Firebase Auth | Authentication |
| Firestore | Real-time database |
| Recharts | Charts & visualizations |
| Lucide React | Icons |
| React Hot Toast | Notifications |

### Backend
| Technology | Purpose |
|------------|---------|
| Python 3.11 | Backend runtime |
| FastAPI + Mangum | API framework (Lambda-optimized) |
| XGBoost | ML model training |
| LSTM (TensorFlow) | Time series forecasting |
| Prophet | Seasonal decomposition |
| Sarvam AI | Hindi TTS/STT |

### AWS Infrastructure
| Service | Purpose |
|---------|---------|
| Lambda | Serverless compute |
| API Gateway | REST API |
| DynamoDB | NoSQL database |
| S3 | Static hosting + data storage |
| SageMaker | Model training & deployment |
| EventBridge | Scheduled tasks (daily retrain) |
| IAM | Access management |

---

## 📱 Features by Role

### 👨‍🌾 Farmer
- **Dashboard** — Overview of listings, orders, revenue
- **Add Crop** — List crops with AI price prediction
- **My Listings** — Manage active crops
- **Orders** — Track incoming orders
- **Crop Price Prediction** — AI-powered forecasts with charts

### 🏪 Wholesaler
- **Dashboard** — Purchase analytics
- **Browse Listings** — Search/filter farmer crops
- **Inventory** — Manage purchased inventory
- **Order History** — Track past purchases

### 🛒 Consumer
- **Home** — Live weather + crop listings
- **Product Listing** — Browse fresh produce
- **Product Details** — View crop info + pricing
- **Cart** — Shopping cart with checkout
- **My Orders** — Track deliveries

### 👔 Admin
- **Dashboard** — Platform analytics (users, revenue, transactions)
- **User Management** — View/filter/search all users
- **Verification** — Approve/reject new users
- **Transactions** — Full order history with search
- **Reports** — Revenue charts + category breakdown

### 📞 IVR (Voice)
- Farmers call → speak crop name in Hindi → get price via TTS
- 60+ crop keywords (Hindi, Romanized, English)
- State detection from phone number
- Sarvam AI integration for Hindi TTS

---

## 🗂️ Project Structure

```
zypher-Agriconnect/
├── src/                          # React frontend
│   ├── pages/
│   │   ├── admin/                # Admin dashboard, reports, users, verification
│   │   ├── consumer/             # Consumer home, products, cart, orders
│   │   ├── farmer/               # Farmer dashboard, add crop, listings, orders
│   │   ├── shared/               # CropPricePrediction, QRScanner
│   │   ├── wholesaler/           # Dashboard, browse, inventory, orders
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   └── RoleSelection.jsx
│   ├── components/               # UI components, ProtectedRoute
│   ├── context/                  # AuthContext, CartContext
│   ├── layouts/                  # Role-based layouts
│   ├── lib/                      # Firebase config
│   └── App.jsx                   # Router + role-based routing
├── backend/
│   ├── ivr/handler.py            # IVR call handler (Exotel + Sarvam TTS)
│   ├── prediction/               # ML pipeline
│   │   ├── api/app.py            # FastAPI endpoints
│   │   ├── data_pipeline.py      # Data collection + training
│   │   ├── models/               # XGBoost, LSTM, ensemble
│   │   └── features/             # Feature engineering
│   ├── sarvam/api.py             # TTS/STT/Translation API
│   ├── aws/
│   │   ├── template.yaml         # SAM template (28 resources)
│   │   └── deploy.py             # Deployment automation
│   └── tests/                    # Test suite
├── firestore.rules               # Firestore security rules
└── .env.production               # Production environment variables
```

---

## 🔧 Local Development

```bash
# Clone
git clone https://github.com/mokshdudeja/zypher-Agriconnect.git
cd zypher-Agriconnect

# Install dependencies
npm install

# Set up environment
cp .env.example .env
# Edit .env with your Firebase config

# Run dev server
npm run dev
```

### Backend (Local)
```bash
cd backend
pip install -r requirements.txt

# Run API
uvicorn prediction.api.app:app --reload --port 8000

# Run IVR handler
uvicorn ivr.handler:app --reload --port 8001
```

---

## 🧪 API Test Examples

### Crop Price Prediction
```bash
curl "https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev/api/predict/wheat/uttar_pradesh"
```
```json
{
  "crop": "wheat",
  "state": "uttar_pradesh",
  "current_price": 2042.5,
  "predicted_price_7d": 2031.42,
  "predicted_price_15d": 2020.0,
  "predicted_price_30d": 2000.0,
  "confidence": 0.7,
  "trend": "stable",
  "factors": ["weather_data_unavailable", "off_season_supply"],
  "model_weights": {"xgboost": 0.4, "lstm": 0.35, "prophet": 0.25}
}
```

### Weather Forecast
```bash
curl "https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev/api/weather/v2?state=uttar_pradesh&days=3"
```

### Crop Recommendation
```bash
curl -X POST "https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev/api/crop-recommend" \
  -H "Content-Type: application/json" \
  -d '{"soil_type":"loamy","pH":6.5,"nitrogen":40,"phosphorus":30,"potassium":20,"rainfall":100,"temperature":25,"season":"kharif"}'
```

---

## 📊 AWS Resources (28 total)

| Type | Resources |
|------|-----------|
| **S3** | agriconnect-data-dev, agriconnect-models-dev, agriconnect-frontend-dev |
| **DynamoDB** | crop_prices, call_logs, user_sessions |
| **Lambda** | api_handler, daily_update, weekly_retrain |
| **API Gateway** | REST API with CORS |
| **EventBridge** | Daily 6 AM IST + Weekly Sunday 2 AM IST |
| **IAM** | Lambda role, SageMaker role + training role |

---

## 🔒 Security

- **Firebase Auth** — Email/password authentication with role-based access
- **Firestore Rules** — Role-based read/write restrictions per collection
- **API Gateway** — CORS configured for frontend origin
- **Environment Variables** — Sensitive keys stored in AWS Secrets Manager
- **S3 Bucket Policy** — Public read for static hosting only

---

## 📈 Future Improvements

1. **CloudFront CDN** — HTTPS + edge caching (pending AWS email verification)
2. **Real XGBoost Models** — Currently using rule-based fallback; train on Agmarknet data
3. **Sagemaker Deployment** — Real-time model serving
4. **Mobile App** — React Native companion
5. **Multi-language** — Tamil, Telugu, Kannada support
6. **Blockchain Traceability** — Crop provenance tracking
7. **Satellite Imagery** — Crop health monitoring

---

## 👥 Team

**Zypher** — Smart India Hackathon 2025

---

## 📄 License

MIT License
