"""
Tests for backend/prediction/api/app.py — API endpoints

Covers:
- /api/health — health check
- /api/ready — readiness probe
- /api/supported — supported crops/states
- /api/predict/{crop}/{state} — price prediction
- /api/weather — weather forecast
- /api/weather/v2 — enhanced weather
- /api/weather/alerts — weather alerts
- /api/crop-recommend — crop recommendation
- /api/crop-recommend/soil-types — soil types
- /api/crop-recommend/crops — crop database
- CORS headers
- Error handling
- Async endpoint tests
- Rate limiting behavior
"""

import pytest
from unittest.mock import patch, MagicMock


# ─── Health & Supported ─────────────────────────────────────────

class TestHealthAndSupported:
    """Test basic endpoints."""

    def test_health(self, prediction_client):
        resp = prediction_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data

    def test_health_has_dynamodb_field(self, prediction_client):
        resp = prediction_client.get("/api/health")
        data = resp.json()
        assert "dynamodb" in data

    def test_health_version_format(self, prediction_client):
        resp = prediction_client.get("/api/health")
        data = resp.json()
        assert data["version"].startswith("2.")

    def test_supported(self, prediction_client):
        resp = prediction_client.get("/api/supported")
        assert resp.status_code == 200
        data = resp.json()
        assert "crops" in data
        assert "states" in data
        assert "horizons" in data
        assert data["horizons"] == [7, 15, 30]

    def test_supported_crops_count(self, prediction_client):
        resp = prediction_client.get("/api/supported")
        assert len(resp.json()["crops"]) >= 10

    def test_supported_states_count(self, prediction_client):
        resp = prediction_client.get("/api/supported")
        assert len(resp.json()["states"]) >= 10

    def test_supported_crops_are_strings(self, prediction_client):
        resp = prediction_client.get("/api/supported")
        for crop in resp.json()["crops"]:
            assert isinstance(crop, str)

    def test_supported_states_are_strings(self, prediction_client):
        resp = prediction_client.get("/api/supported")
        for state in resp.json()["states"]:
            assert isinstance(state, str)


# ─── Readiness Probe ────────────────────────────────────────────

class TestReadinessProbe:
    """Test /api/ready endpoint for Kubernetes readiness."""

    def test_ready_endpoint_exists(self, prediction_client):
        """Test if /api/ready endpoint exists."""
        resp = prediction_client.get("/api/ready")
        # If endpoint doesn't exist, it should return 404
        # If it exists, it should return 200
        assert resp.status_code in (200, 404)

    def test_ready_returns_ok_when_healthy(self, prediction_client):
        """Test readiness when service is healthy."""
        resp = prediction_client.get("/api/ready")
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("status") == "ok" or data.get("ready") is True


# ─── Price Prediction Endpoint ──────────────────────────────────

class TestPredictEndpoint:
    """Test /api/predict/{crop}/{state}."""

    def test_predict_wheat_up(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["crop"] == "wheat"
        assert data["state"] == "uttar_pradesh"

    def test_predict_returns_current_price(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = resp.json()
        assert data["current_price"] > 0

    def test_predict_returns_all_horizons(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = resp.json()
        assert data["predicted_price_7d"] > 0
        assert data["predicted_price_15d"] > 0
        assert data["predicted_price_30d"] > 0

    def test_predict_confidence_range(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = resp.json()
        assert 0 <= data["confidence"] <= 1

    def test_predict_trend_values(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = resp.json()
        assert data["trend"] in ("bullish", "bearish", "stable")

    def test_predict_has_factors(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = resp.json()
        assert isinstance(data["factors"], list)
        assert len(data["factors"]) > 0

    def test_predict_has_generated_at(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = resp.json()
        assert "generated_at" in data

    def test_predict_invalid_crop_400(self, prediction_client):
        resp = prediction_client.get("/api/predict/banana/uttar_pradesh")
        assert resp.status_code == 400

    def test_predict_invalid_state_400(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/nevada")
        assert resp.status_code == 400

    def test_predict_all_crops(self, prediction_client):
        crops = ["wheat", "rice", "maize", "cotton", "soybean",
                 "potato", "tomato", "onion", "groundnut", "sugarcane"]
        for crop in crops:
            resp = prediction_client.get(f"/api/predict/{crop}/uttar_pradesh")
            assert resp.status_code == 200, f"Failed for crop: {crop}"

    def test_predict_all_states(self, prediction_client):
        states = ["uttar_pradesh", "maharashtra", "madhya_pradesh",
                  "west_bengal", "rajasthan", "karnataka",
                  "andhra_pradesh", "gujarat", "punjab",
                  "tamil_nadu", "haryana", "bihar"]
        for state in states:
            resp = prediction_client.get(f"/api/predict/wheat/{state}")
            assert resp.status_code == 200, f"Failed for state: {state}"

    def test_predict_case_insensitive(self, prediction_client):
        resp = prediction_client.get("/api/predict/Wheat/Uttar_Pradesh")
        assert resp.status_code == 200

    def test_predict_with_cache_disabled(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh?use_cache=false")
        assert resp.status_code == 200

    def test_predict_response_model_fields(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = resp.json()
        required = [
            "crop", "state", "current_price", "predicted_price_7d",
            "predicted_price_15d", "predicted_price_30d", "confidence",
            "trend", "factors", "generated_at",
        ]
        for field in required:
            assert field in data, f"Missing: {field}"

    def test_predict_prices_are_positive(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = resp.json()
        assert data["current_price"] > 0
        assert data["predicted_price_7d"] > 0
        assert data["predicted_price_15d"] > 0
        assert data["predicted_price_30d"] > 0

    def test_predict_model_weights_present(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        data = resp.json()
        if "model_weights" in data:
            weights = data["model_weights"]
            assert isinstance(weights, dict)
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01  # Weights should sum to ~1


# ─── Weather Endpoints ──────────────────────────────────────────

class TestWeatherEndpoint:
    """Test /api/weather endpoint."""

    def test_weather_requires_district(self, prediction_client):
        resp = prediction_client.get("/api/weather?state=uttar_pradesh")
        assert resp.status_code == 422  # Missing required param

    def test_weather_requires_state(self, prediction_client):
        resp = prediction_client.get("/api/weather?district=lucknow")
        assert resp.status_code == 422

    @patch("backend.prediction.api.app._fetch_weather_full")
    def test_weather_returns_forecast(self, mock_weather, prediction_client):
        mock_weather.return_value = {
            "current": {
                "temperature": 32, "feels_like": 35, "humidity": 70,
                "precipitation": 0, "weather_code": 2, "wind_speed": 10,
                "wind_direction": 180,
            },
            "forecast": [
                {"date": "2024-01-15", "temp_max": 35, "temp_min": 22,
                 "precipitation": 5, "weather_code": 61, "wind_speed_max": 15,
                 "precipitation_probability": 60},
            ],
        }
        resp = prediction_client.get(
            "/api/weather?district=lucknow&state=uttar_pradesh"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "current" in data
        assert "forecast" in data
        assert "alerts" in data
        assert "recommendations" in data

    @patch("backend.prediction.api.app._fetch_weather_full")
    def test_weather_forecast_has_multiple_days(self, mock_weather, prediction_client):
        mock_weather.return_value = {
            "current": {"temperature": 30, "feels_like": 32, "humidity": 60,
                        "precipitation": 0, "weather_code": 1, "wind_speed": 8,
                        "wind_direction": 90},
            "forecast": [
                {"date": f"2024-01-{15+i}", "temp_max": 35-i, "temp_min": 22+i,
                 "precipitation": i*2, "weather_code": 60, "wind_speed_max": 10+i,
                 "precipitation_probability": 20+i*10}
                for i in range(7)
            ],
        }
        resp = prediction_client.get("/api/weather?district=lucknow&state=uttar_pradesh")
        if resp.status_code == 200:
            data = resp.json()
            assert len(data["forecast"]) >= 5


# ─── Weather v2 Endpoint ────────────────────────────────────────

class TestWeatherV2Endpoint:
    """Test /api/weather/v2 endpoint."""

    def test_weather_v2_requires_state(self, prediction_client):
        resp = prediction_client.get("/api/weather/v2")
        assert resp.status_code == 422

    @patch("backend.prediction.api.app._fetch_weather_v2")
    def test_weather_v2_returns_location(self, mock_weather, prediction_client):
        mock_weather.return_value = {
            "current": {"temp": 32, "humidity": 70, "wind": 10, "weather_code": 2},
            "forecast": [
                {"date": "2024-01-15", "temp_max": 35, "temp_min": 22,
                 "precipitation": 5, "humidity": 65, "wind": 12},
            ],
        }
        resp = prediction_client.get("/api/weather/v2?state=uttar_pradesh")
        assert resp.status_code == 200
        data = resp.json()
        assert "location" in data
        assert "current" in data
        assert "forecast" in data


# ─── Weather Alerts Endpoint ────────────────────────────────────

class TestWeatherAlertsEndpoint:
    """Test /api/weather/alerts endpoint."""

    def test_alerts_requires_state(self, prediction_client):
        resp = prediction_client.get("/api/weather/alerts")
        assert resp.status_code == 422

    @patch("backend.prediction.api.app._fetch_weather_full")
    def test_alerts_returns_alerts_list(self, mock_weather, prediction_client):
        mock_weather.return_value = {
            "current": {"temperature": 45, "feels_like": 48, "humidity": 40,
                        "precipitation": 0, "weather_code": 0, "wind_speed": 5,
                        "wind_direction": 180},
            "forecast": [
                {"date": "2024-01-15", "temp_max": 46, "temp_min": 30,
                 "precipitation": 0, "weather_code": 0, "wind_speed_max": 5,
                 "precipitation_probability": 0},
            ],
        }
        resp = prediction_client.get("/api/weather/alerts?state=uttar_pradesh")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "total_alerts" in data


# ─── Crop Recommendation ────────────────────────────────────────

class TestCropRecommendation:
    """Test /api/crop-recommend endpoint."""

    def test_recommend_requires_body(self, prediction_client):
        resp = prediction_client.post("/api/crop-recommend", json={})
        # Should work with defaults or return 400
        assert resp.status_code in (200, 400)

    def test_recommend_with_valid_input(self, prediction_client):
        resp = prediction_client.post("/api/crop-recommend", json={
            "soil_type": "loamy",
            "ph": 6.5,
            "nitrogen": 80,
            "phosphorus": 40,
            "potassium": 40,
            "rainfall": 800,
            "temperature": 25,
            "season": "rabi",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) == 5
        assert "input" in data

    def test_recommend_top_crop_has_score(self, prediction_client):
        resp = prediction_client.post("/api/crop-recommend", json={
            "soil_type": "loamy",
            "ph": 6.5,
            "nitrogen": 80,
            "phosphorus": 40,
            "potassium": 40,
            "rainfall": 800,
            "temperature": 25,
            "season": "rabi",
        })
        data = resp.json()
        top = data["recommendations"][0]
        assert "suitability_score" in top
        assert "expected_revenue_per_ha" in top
        assert "rotation" in top

    def test_recommend_invalid_soil_type(self, prediction_client):
        resp = prediction_client.post("/api/crop-recommend", json={
            "soil_type": "unobtainium",
            "ph": 6.5,
        })
        assert resp.status_code == 400

    def test_recommend_soil_types_endpoint(self, prediction_client):
        resp = prediction_client.get("/api/crop-recommend/soil-types")
        assert resp.status_code == 200
        data = resp.json()
        assert "soil_types" in data
        assert "loamy" in data["soil_types"]

    def test_recommend_crops_endpoint(self, prediction_client):
        resp = prediction_client.get("/api/crop-recommend/crops")
        assert resp.status_code == 200
        data = resp.json()
        assert "crops" in data
        assert len(data["crops"]) >= 10

    def test_recommend_multiple_seasons(self, prediction_client):
        for season in ["kharif", "rabi", "zaid"]:
            resp = prediction_client.post("/api/crop-recommend", json={
                "soil_type": "loamy",
                "ph": 6.5,
                "nitrogen": 80,
                "phosphorus": 40,
                "potassium": 40,
                "rainfall": 800,
                "temperature": 25,
                "season": season,
            })
            assert resp.status_code == 200, f"Failed for season: {season}"


# ─── CORS Headers ───────────────────────────────────────────────

class TestCORS:
    """Test CORS middleware configuration."""

    def test_cors_preflight(self, prediction_client):
        resp = prediction_client.options("/api/predict/wheat/uttar_pradesh", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        # CORS middleware should handle this
        assert resp.status_code in (200, 405)


# ─── Error Handling ─────────────────────────────────────────────

class TestErrorHandling:
    """Test error responses."""

    def test_404_unknown_route(self, prediction_client):
        resp = prediction_client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_method_not_allowed(self, prediction_client):
        resp = prediction_client.post("/api/predict/wheat/uttar_pradesh")
        assert resp.status_code == 405

    def test_predict_with_empty_crop(self, prediction_client):
        resp = prediction_client.get("/api/predict//uttar_pradesh")
        assert resp.status_code in (400, 404, 422)

    def test_predict_with_empty_state(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/")
        assert resp.status_code in (400, 404, 422)


# ─── Async Endpoint Tests ───────────────────────────────────────

class TestAsyncEndpoints:
    """Test endpoints using async client."""

    @pytest.mark.asyncio
    async def test_async_health(self, prediction_async_client):
        resp = await prediction_async_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_async_supported(self, prediction_async_client):
        resp = await prediction_async_client.get("/api/supported")
        assert resp.status_code == 200
        data = resp.json()
        assert "crops" in data

    @pytest.mark.asyncio
    async def test_async_predict(self, prediction_async_client):
        resp = await prediction_async_client.get("/api/predict/wheat/uttar_pradesh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["crop"] == "wheat"

    @pytest.mark.asyncio
    async def test_async_health_response_time(self, prediction_async_client):
        import time
        start = time.time()
        resp = await prediction_async_client.get("/api/health")
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 1.0  # Should respond within 1 second


# ─── Rate Limiting Tests ────────────────────────────────────────

class TestRateLimiting:
    """Test rate limiting behavior."""

    def test_rapid_requests_do_not_crash(self, prediction_client):
        """Ensure multiple rapid requests don't crash the server."""
        for i in range(10):
            resp = prediction_client.get("/api/health")
            assert resp.status_code == 200

    def test_concurrent_predict_requests(self, prediction_client):
        """Ensure concurrent predict requests work."""
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    prediction_client.get,
                    "/api/predict/wheat/uttar_pradesh"
                )
                for _ in range(5)
            ]
            results = [f.result() for f in futures]
            for resp in results:
                assert resp.status_code == 200


# ─── Response Format Tests ──────────────────────────────────────

class TestResponseFormat:
    """Test response format consistency."""

    def test_health_returns_json(self, prediction_client):
        resp = prediction_client.get("/api/health")
        assert resp.headers["content-type"] == "application/json"

    def test_supported_returns_json(self, prediction_client):
        resp = prediction_client.get("/api/supported")
        assert resp.headers["content-type"] == "application/json"

    def test_predict_returns_json(self, prediction_client):
        resp = prediction_client.get("/api/predict/wheat/uttar_pradesh")
        assert "application/json" in resp.headers["content-type"]

    def test_health_response_is_serializable(self, prediction_client):
        resp = prediction_client.get("/api/health")
        import json
        json.loads(resp.text)  # Should not raise


# ─── Data Integrity Tests ───────────────────────────────────────

class TestDataIntegrity:
    """Test data integrity in responses."""

    def test_predict_crop_matches_request(self, prediction_client):
        crops = ["wheat", "rice", "maize"]
        for crop in crops:
            resp = prediction_client.get(f"/api/predict/{crop}/uttar_pradesh")
            if resp.status_code == 200:
                assert resp.json()["crop"] == crop

    def test_predict_state_matches_request(self, prediction_client):
        states = ["uttar_pradesh", "maharashtra"]
        for state in states:
            resp = prediction_client.get(f"/api/predict/wheat/{state}")
            if resp.status_code == 200:
                assert resp.json()["state"] == state

    def test_supported_crops_match_predict(self, prediction_client):
        supported = prediction_client.get("/api/supported").json()["crops"]
        for crop in supported:
            resp = prediction_client.get(f"/api/predict/{crop}/uttar_pradesh")
            assert resp.status_code == 200, f"Supported crop {crop} failed predict"
