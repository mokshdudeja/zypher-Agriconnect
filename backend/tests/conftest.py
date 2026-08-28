"""
AgriConnect — Test Fixtures & Configuration

Shared fixtures for all test modules:
- FastAPI TestClient / AsyncClient for each app
- Mock AWS clients (DynamoDB, S3, SageMaker, Lambda)
- Factory fixtures for crop data and mandi prices
- Override fixtures: override_auth, override_db
- Auto-reset dependency overrides after each test
"""

import os
import sys
import json
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# ─── Ensure backend is importable ────────────────────────────────

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Set env vars before importing any modules
os.environ.setdefault("USE_DYNAMODB", "false")
os.environ.setdefault("SARVAM_API_KEY", "test-sarvam-key")
os.environ.setdefault("EXOTEL_SID", "test-exotel-sid")
os.environ.setdefault("EXOTEL_API_KEY", "test-exotel-key")
os.environ.setdefault("API_BASE_URL", "http://localhost:8000")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")


# ─── Parametrize Data ───────────────────────────────────────────

SUPPORTED_CROPS = [
    "wheat", "rice", "maize", "cotton", "soybean",
    "potato", "tomato", "onion", "groundnut", "sugarcane",
]

INDIAN_STATES = [
    "uttar_pradesh", "maharashtra", "madhya_pradesh", "punjab",
    "haryana", "karnataka", "tamil_nadu", "andhra_pradesh",
    "telangana", "rajasthan", "gujarat",
]

HINDI_CROP_KEYWORDS = [
    "गेहूं", "चावल", "मक्का", "कपास", "सोयाबीन",
    "आलू", "टमाटर", "प्याज", "मूंगफली", "गन्ना",
]

ROMANIZED_KEYWORDS = [
    "gehun", "dhaan", "makka", "kapas", "soyabean",
    "aalo", "tamatar", "pyaaz", "moongfali", "ganna",
]

ENGLISH_KEYWORDS = [
    "wheat", "rice", "corn", "cotton", "soybean",
    "potato", "tomato", "onion", "peanut", "sugarcane",
]


# ─── IVR App Fixtures ───────────────────────────────────────────

@pytest.fixture(scope="session")
def ivr_app():
    """Import the IVR FastAPI app."""
    from backend.ivr.handler import app
    return app


@pytest.fixture(scope="session")
def ivr_client(ivr_app) -> TestClient:
    """Sync TestClient for the IVR app."""
    return TestClient(ivr_app, raise_server_exceptions=False)


@pytest.fixture
def ivr_client_fresh(ivr_app) -> TestClient:
    """Fresh TestClient per test (no state sharing)."""
    return TestClient(ivr_app, raise_server_exceptions=False)


@pytest.fixture
async def ivr_async_client(ivr_app) -> AsyncGenerator[AsyncClient, None]:
    """Async TestClient for the IVR app."""
    transport = ASGITransport(app=ivr_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ─── Prediction App Fixtures ────────────────────────────────────

@pytest.fixture(scope="session")
def prediction_app():
    """Import the Prediction FastAPI app."""
    from backend.prediction.api.app import app
    return app


@pytest.fixture(scope="session")
def prediction_client(prediction_app) -> TestClient:
    """Sync TestClient for the Prediction app."""
    return TestClient(prediction_app, raise_server_exceptions=False)


@pytest.fixture
def prediction_client_fresh(prediction_app) -> TestClient:
    """Fresh TestClient per test."""
    return TestClient(prediction_app, raise_server_exceptions=False)


@pytest.fixture
async def prediction_async_client(prediction_app) -> AsyncGenerator[AsyncClient, None]:
    """Async TestClient for the Prediction app."""
    transport = ASGITransport(app=prediction_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ─── Sarvam App Fixtures ────────────────────────────────────────

@pytest.fixture(scope="session")
def sarvam_app():
    """Import the Sarvam FastAPI app."""
    from backend.sarvam.api import app
    return app


@pytest.fixture(scope="session")
def sarvam_client(sarvam_app) -> TestClient:
    """Sync TestClient for the Sarvam app."""
    return TestClient(sarvam_app, raise_server_exceptions=False)


@pytest.fixture
async def sarvam_async_client(sarvam_app) -> AsyncGenerator[AsyncClient, None]:
    """Async TestClient for the Sarvam app."""
    transport = ASGITransport(app=sarvam_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ─── Mock AWS Clients ───────────────────────────────────────────

@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table with in-memory storage."""
    table = MagicMock()
    table.put_item = MagicMock()
    table.get_item = MagicMock(return_value={"Item": None})
    table.query = MagicMock(return_value={"Items": []})
    table.scan = MagicMock(return_value={"Items": []})
    table.delete_item = MagicMock()
    table.update_item = MagicMock()
    return table


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    client = MagicMock()
    client.upload_file = MagicMock()
    client.download_file = MagicMock()
    client.head_object = MagicMock(side_effect=Exception("NoSuchKey"))
    client.list_objects_v2 = MagicMock(return_value={"Contents": []})
    client.get_object = MagicMock()
    client.put_object = MagicMock()
    return client


@pytest.fixture
def mock_sagemaker_client():
    """Mock SageMaker client."""
    client = MagicMock()
    client.create_training_job = MagicMock(return_value={
        "TrainingJobArn": "arn:aws:sagemaker:ap-south-1:123456:training-job/test"
    })
    client.describe_training_job = MagicMock(return_value={
        "TrainingJobStatus": "Completed",
        "ModelArtifacts": {"S3ModelArtifacts": "s3://bucket/model.tar.gz"},
    })
    client.create_model = MagicMock()
    client.create_endpoint_config = MagicMock()
    client.create_endpoint = MagicMock()
    client.describe_endpoint = MagicMock(return_value={"EndpointStatus": "InService"})
    return client


@pytest.fixture
def mock_lambda_client():
    """Mock Lambda client."""
    client = MagicMock()
    client.invoke = MagicMock(return_value={
        "StatusCode": 200,
        "Payload": MagicMock(read=MagicMock(return_value=json.dumps({"statusCode": 200}).encode())),
    })
    return client


@pytest.fixture
def mock_requests(monkeypatch):
    """Mock requests library for external API calls."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {}
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = ""

    def mock_get(*args, **kwargs):
        return mock_resp

    def mock_post(*args, **kwargs):
        return mock_resp

    monkeypatch.setattr("requests.get", mock_get)
    monkeypatch.setattr("requests.post", mock_post)
    return mock_resp


# ─── Factory Fixtures ───────────────────────────────────────────

@pytest.fixture
def crop_data_factory():
    """Factory for creating crop prediction data."""
    def _factory(
        crop: str = "wheat",
        state: str = "uttar_pradesh",
        current_price: float = 2150.0,
        predicted_7d: float = 2180.0,
        predicted_15d: float = 2200.0,
        predicted_30d: float = 2100.0,
        confidence: float = 0.87,
        trend: str = "bullish",
    ):
        return {
            "crop": crop,
            "state": state,
            "current_price": current_price,
            "predicted_price_7d": predicted_7d,
            "predicted_price_15d": predicted_15d,
            "predicted_price_30d": predicted_30d,
            "confidence": confidence,
            "trend": trend,
            "factors": ["high_temperature", "harvest_season"],
            "model_weights": {"xgboost": 0.40, "lstm": 0.35, "prophet": 0.25},
            "cached": False,
            "generated_at": datetime.now().isoformat(),
        }
    return _factory


@pytest.fixture
def mandi_price_factory():
    """Factory for creating mandi price records."""
    def _factory(
        crop: str = "Wheat",
        state: str = "Uttar Pradesh",
        district: str = "Lucknow",
        market: str = "Lucknow",
        min_price: float = 2000.0,
        max_price: float = 2300.0,
        modal_price: float = 2150.0,
        arrival_qty: float = 500.0,
        days_back: int = 0,
    ):
        date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        return {
            "date": date,
            "state": state,
            "district": district,
            "market": market,
            "commodity": crop,
            "variety": "FAQ",
            "min_price": min_price,
            "max_price": max_price,
            "modal_price": modal_price,
            "arrival_quantity": arrival_qty,
            "unit": "Quintal",
        }
    return _factory


@pytest.fixture
def weather_data_factory():
    """Factory for creating OpenMeteo weather records."""
    def _factory(
        temp_max: float = 35.0,
        temp_min: float = 22.0,
        temp_mean: float = 28.5,
        precipitation: float = 5.0,
        rain: float = 5.0,
        wind_max: float = 15.0,
        days_back: int = 0,
    ):
        date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        return {
            "date": date,
            "temp_max": temp_max,
            "temp_min": temp_min,
            "temp_mean": temp_mean,
            "precipitation": precipitation,
            "rain": rain,
            "wind_max": wind_max,
        }
    return _factory


@pytest.fixture
def exotel_webhook_factory():
    """Factory for creating Exotel webhook form data."""
    def _factory(
        call_sid: str = "test-call-001",
        from_number: str = "+919876543210",
        to_number: str = "+911234567890",
        direction: str = "inbound",
        speech_result: str = "",
        confidence: str = "0.95",
    ):
        data = {
            "CallSid": call_sid,
            "From": from_number,
            "To": to_number,
            "Direction": direction,
        }
        if speech_result:
            data["SpeechResult"] = speech_result
            data["Confidence"] = confidence
        return data
    return _factory


# ─── IVR-Specific Fixtures ──────────────────────────────────────

@pytest.fixture
def ivr_audio_cache():
    """Provide access to the IVR audio cache for testing."""
    from backend.ivr.handler import _audio_cache
    return _audio_cache


@pytest.fixture
def ivr_call_log_memory():
    """Provide access to the IVR in-memory call log for testing."""
    from backend.ivr.handler import _call_log_memory
    # Clear before test
    _call_log_memory.clear()
    yield _call_log_memory
    # Clear after test
    _call_log_memory.clear()


@pytest.fixture(autouse=True)
def reset_ivr_caches(ivr_audio_cache, ivr_call_log_memory):
    """Auto-reset IVR caches before and after each test."""
    ivr_audio_cache.clear()
    ivr_call_log_memory.clear()
    yield
    ivr_audio_cache.clear()
    ivr_call_log_memory.clear()


# ─── Prediction-Specific Fixtures ───────────────────────────────

@pytest.fixture
def prediction_memory_cache():
    """Provide access to the prediction in-memory cache."""
    from backend.prediction.api.app import _memory_cache
    _memory_cache.clear()
    yield _memory_cache
    _memory_cache.clear()


# ─── Override Fixtures ──────────────────────────────────────────

@pytest.fixture
def override_db():
    """Override database dependencies for testing."""
    from backend.prediction.api import app as pred_app
    mock_table = MagicMock()
    mock_table.get_item.return_value = {"Item": None}
    mock_table.put_item.return_value = {}
    mock_table.query.return_value = {"Items": []}
    mock_table.scan.return_value = {"Items": []}

    # Override DynamoDB dependency if the app has one
    if hasattr(pred_app, "dependency_overrides"):
        original_overrides = pred_app.dependency_overrides.copy()
        yield mock_table
        pred_app.dependency_overrides.clear()
        pred_app.dependency_overrides.update(original_overrides)
    else:
        yield mock_table


@pytest.fixture
def override_auth():
    """Override authentication dependencies for testing."""
    from backend.prediction.api import app as pred_app

    def mock_get_current_user():
        return {
            "user_id": "test-user-001",
            "email": "test@agriconnect.in",
            "role": "farmer",
            "phone": "+919876543210",
        }

    # Override auth dependency if the app has one
    if hasattr(pred_app, "dependency_overrides"):
        original_overrides = pred_app.dependency_overrides.copy()
        # Look for auth-related dependencies to override
        for dep_name in list(pred_app.dependency_overrides.keys()):
            if "auth" in str(dep_name).lower() or "user" in str(dep_name).lower():
                pred_app.dependency_overrides[dep_name] = mock_get_current_user
        yield mock_get_current_user
        pred_app.dependency_overrides.clear()
        pred_app.dependency_overrides.update(original_overrides)
    else:
        yield mock_get_current_user


@pytest.fixture
def mock_db_session():
    """Mock database session for SQLAlchemy-based apps."""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.execute = MagicMock()
    session.scalar = MagicMock()
    session.get = MagicMock()
    session.merge = MagicMock()
    session.delete = MagicMock()
    session.flush = MagicMock()
    session.expire_all = MagicMock()
    return session


# ─── Data Pipeline Fixtures ─────────────────────────────────────

@pytest.fixture
def sample_mandi_df():
    """Create a sample mandi DataFrame for pipeline tests."""
    import pandas as pd
    import numpy as np

    dates = pd.date_range(end=datetime.now(), periods=365, freq="D")
    np.random.seed(42)
    base_price = 2150
    noise = np.random.normal(0, 50, len(dates))
    trend = np.linspace(0, 200, len(dates))
    prices = base_price + trend + noise

    df = pd.DataFrame({
        "date": dates,
        "price": prices,
        "min_price": prices - 100,
        "max_price": prices + 100,
        "modal_price": prices,
        "arrival_qty": np.random.uniform(100, 1000, len(dates)),
        "crop": "wheat",
        "state": "uttar_pradesh",
        "year": dates.year,
        "month": dates.month,
        "day_of_year": dates.dayofyear,
        "day_of_week": dates.dayofweek,
        "season": dates.month.map(lambda m: "kharif" if 6 <= m <= 10 else ("rabi" if m in (11, 12, 1, 2, 3) else "zaid")),
        "temp_max": np.random.uniform(25, 40, len(dates)),
        "temp_min": np.random.uniform(10, 25, len(dates)),
        "temp_mean": np.random.uniform(18, 32, len(dates)),
        "precipitation": np.random.exponential(5, len(dates)),
        "rain": np.random.exponential(5, len(dates)),
        "wind_max": np.random.uniform(5, 25, len(dates)),
    })
    return df


@pytest.fixture
def sample_featured_df(sample_mandi_df):
    """Create a sample featured DataFrame with all engineered features."""
    import sys
    sys.path.insert(0, str(BACKEND_ROOT))
    from backend.prediction.data_pipeline import engineer_features
    return engineer_features(sample_mandi_df)


# ─── Temp Directory ─────────────────────────────────────────────

@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
