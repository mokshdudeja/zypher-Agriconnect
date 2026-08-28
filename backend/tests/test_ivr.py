"""
Tests for backend/ivr/handler.py

Covers:
- Crop name parsing (Hindi Devanagari, Romanized, English)
- State detection from phone numbers
- TwiML XML generation
- Incoming call webhook
- Gather speech callback
- Audio serving
- TTS preview
- Test crop lookup
- Call stats
- Supported crops list
- Outbound call initiation
- Exotel status callback
- Fallback to <Say> when Sarvam TTS fails
"""

import pytest
from unittest.mock import patch, MagicMock


# ─── Crop Name Parsing ──────────────────────────────────────────

class TestParseCropName:
    """Test crop name parsing from speech transcripts."""

    def test_parse_hindi_devanagari_wheat(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("गेहूं") == "wheat"

    def test_parse_hindi_devanagari_rice(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("चावल") == "rice"

    def test_parse_hindi_devanagari_potato(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("आलू") == "potato"

    def test_parse_hindi_devanagari_onion(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("प्याज") == "onion"

    def test_parse_hindi_devanagari_cotton(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("कपास") == "cotton"

    def test_parse_hindi_devanagari_sugarcane(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("गन्ना") == "sugarcane"

    def test_parse_romanized_gehun(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("gehun") == "wheat"

    def test_parse_romanized_dhaan(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("dhaan") == "rice"

    def test_parse_romanized_aalo(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("aalo") == "potato"

    def test_parse_romanized_pyaaz(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("pyaaz") == "onion"

    def test_parse_english_wheat(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("wheat") == "wheat"

    def test_parse_english_rice(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("rice") == "rice"

    def test_parse_english_corn(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("corn") == "maize"

    def test_parse_english_peanut(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("peanut") == "groundnut"

    def test_parse_sentence_with_crop(self):
        from backend.ivr.handler import parse_crop_name
        result = parse_crop_name("मुझे गेहूं की कीमत बताओ")
        assert result == "wheat"

    def test_parse_english_sentence(self):
        from backend.ivr.handler import parse_crop_name
        result = parse_crop_name("what is the price of wheat")
        assert result == "wheat"

    def test_parse_empty_string(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("") is None

    def test_parse_none(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name(None) is None

    def test_parse_unrecognized_text(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("hello world how are you") is None

    def test_parse_makka(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("makka") == "maize"

    def test_parse_kapas(self):
        from backend.ivr.handler import parse_crop_name
        assert parse_crop_name("kapas") == "cotton"


# ─── State Detection from Phone ─────────────────────────────────

class TestDetectStateFromPhone:
    """Test state detection from Indian phone number prefixes."""

    def test_up_prefix(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("+919876543210") == "uttar_pradesh"

    def test_maharashtra_prefix(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("+917212345678") == "maharashtra"

    def test_mp_prefix(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("+917712345678") == "madhya_pradesh"

    def test_gujarat_prefix(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("+918212345678") == "gujarat"

    def test_rajasthan_prefix(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("+918512345678") == "rajasthan"

    def test_punjab_prefix(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("+918812345678") == "punjab"

    def test_bihar_prefix(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("+919012345678") == "bihar"

    def test_west_bengal_prefix(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("+919212345678") == "west_bengal"

    def test_karnataka_prefix(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("+919412345678") == "karnataka"

    def test_short_number_fallback(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("1234") == "uttar_pradesh"

    def test_with_country_code(self):
        from backend.ivr.handler import detect_state_from_phone
        assert detect_state_from_phone("919876543210") == "uttar_pradesh"


# ─── TwiML XML Generation ───────────────────────────────────────

class TestTwiMLGeneration:
    """Test TwiML XML generation functions."""

    def test_twiml_say(self):
        from backend.ivr.handler import twiml_say
        xml = twiml_say("नमस्ते")
        assert "<Say" in xml
        assert "hi-IN" in xml
        assert "नमस्ते" in xml

    def test_twiml_say_english(self):
        from backend.ivr.handler import twiml_say
        xml = twiml_say("Hello", language="en-IN")
        assert "en-IN" in xml
        assert "Hello" in xml

    def test_twiml_play(self):
        from backend.ivr.handler import twiml_play
        xml = twiml_play("https://example.com/audio.wav")
        assert "<Play>" in xml
        assert "https://example.com/audio.wav" in xml

    def test_twiml_gather(self):
        from backend.ivr.handler import twiml_gather
        xml = twiml_gather(
            action_url="https://example.com/api/ivr/gather",
            text="बोलिए",
        )
        assert "<Gather" in xml
        assert "input=\"speech\"" in xml
        assert "action=" in xml
        assert "speech" in xml

    def test_twiml_response(self):
        from backend.ivr.handler import twiml_response
        xml = twiml_response(["<Say>hello</Say>", "<Hangup/>"])
        assert '<?xml version="1.0"' in xml
        assert "<Response>" in xml
        assert "</Response>" in xml
        assert "<Say>hello</Say>" in xml
        assert "<Hangup/>" in xml

    def test_twiml_hangup(self):
        from backend.ivr.handler import twiml_hangup
        xml = twiml_hangup()
        assert "<Hangup/>" in xml

    def test_twiml_redirect(self):
        from backend.ivr.handler import twiml_redirect
        xml = twiml_redirect("https://example.com/api/ivr/incoming")
        assert "<Redirect" in xml
        assert "https://example.com/api/ivr/incoming" in xml

    def test_twiml_xml_valid_structure(self):
        """Ensure generated TwiML is well-formed XML."""
        from backend.ivr.handler import twiml_response, twiml_say, twiml_hangup
        xml = twiml_response([twiml_say("test"), twiml_hangup()])
        # Basic XML validation
        assert xml.startswith("<?xml")
        assert xml.count("<Response>") == 1
        assert xml.count("</Response>") == 1
        assert xml.count("<Say") == 1
        assert xml.count("<Hangup/>") == 1


# ─── Price Response Text Generation ─────────────────────────────

class TestGeneratePriceResponse:
    """Test Hindi price response text generation."""

    def test_bullish_response(self):
        from backend.ivr.handler import generate_price_response_text
        prediction = {
            "current_price": 2150,
            "predicted_price_7d": 2200,
            "trend": "bullish",
        }
        text = generate_price_response_text("wheat", "uttar_pradesh", prediction)
        assert "गेहूं" in text
        assert "2150" in text
        assert "2200" in text
        assert "बढ़ रही है" in text

    def test_bearish_response(self):
        from backend.ivr.handler import generate_price_response_text
        prediction = {
            "current_price": 2500,
            "predicted_price_7d": 2400,
            "trend": "bearish",
        }
        text = generate_price_response_text("rice", "maharashtra", prediction)
        assert "चावल" in text
        assert "गिर रही है" in text

    def test_stable_response(self):
        from backend.ivr.handler import generate_price_response_text
        prediction = {
            "current_price": 1850,
            "predicted_price_7d": 1860,
            "trend": "stable",
        }
        text = generate_price_response_text("maize", "punjab", prediction)
        assert "मक्का" in text
        assert "स्थिर" in text

    def test_maharashtra_state_hindi(self):
        from backend.ivr.handler import generate_price_response_text
        prediction = {"current_price": 6200, "predicted_price_7d": 6300, "trend": "bullish"}
        text = generate_price_response_text("cotton", "maharashtra", prediction)
        assert "महाराष्ट्र" in text


# ─── IVR Incoming Endpoint ──────────────────────────────────────

class TestIVRIncoming:
    """Test the incoming call webhook."""

    def test_incoming_returns_xml(self, ivr_client):
        response = ivr_client.post("/api/ivr/incoming", data={
            "CallSid": "test-001",
            "From": "+919876543210",
            "To": "+911234567890",
            "Direction": "inbound",
        })
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]

    def test_incoming_contains_welcome_message(self, ivr_client):
        response = ivr_client.post("/api/ivr/incoming", data={
            "CallSid": "test-002",
            "From": "+919876543210",
            "To": "+911234567890",
            "Direction": "inbound",
        })
        xml = response.text
        assert "नमस्ते" in xml
        assert "कृषि सेवा" in xml

    def test_incoming_contains_gather(self, ivr_client):
        response = ivr_client.post("/api/ivr/incoming", data={
            "CallSid": "test-003",
            "From": "+919876543210",
            "To": "+911234567890",
            "Direction": "inbound",
        })
        assert "<Gather" in response.text
        assert "input=\"speech\"" in response.text

    def test_incoming_logs_call(self, ivr_client, ivr_call_log_memory):
        ivr_client.post("/api/ivr/incoming", data={
            "CallSid": "test-log-001",
            "From": "+919876543210",
            "To": "+911234567890",
            "Direction": "inbound",
        })
        assert len(ivr_call_log_memory) >= 1
        assert ivr_call_log_memory[-1]["call_id"] == "test-log-001"

    def test_incoming_detects_state_from_phone(self, ivr_client, ivr_call_log_memory):
        ivr_client.post("/api/ivr/incoming", data={
            "CallSid": "test-state-001",
            "From": "+917212345678",  # Maharashtra prefix
            "To": "+911234567890",
            "Direction": "inbound",
        })
        log = [l for l in ivr_call_log_memory if l["call_id"] == "test-state-001"]
        assert len(log) == 1
        assert log[0]["state"] == "maharashtra"


# ─── IVR Gather Endpoint ────────────────────────────────────────

class TestIVRGather:
    """Test the gather speech callback."""

    def test_gather_with_hindi_crop(self, ivr_client):
        response = ivr_client.post(
            "/api/ivr/gather?state=uttar_pradesh",
            data={
                "CallSid": "gather-001",
                "From": "+919876543210",
                "SpeechResult": "गेहूं",
                "Confidence": "0.95",
            },
        )
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]

    def test_gather_with_english_crop(self, ivr_client):
        response = ivr_client.post(
            "/api/ivr/gather?state=uttar_pradesh",
            data={
                "CallSid": "gather-002",
                "From": "+919876543210",
                "SpeechResult": "wheat",
                "Confidence": "0.90",
            },
        )
        assert response.status_code == 200

    def test_gather_with_romanized_crop(self, ivr_client):
        response = ivr_client.post(
            "/api/ivr/gather?state=uttar_pradesh",
            data={
                "CallSid": "gather-003",
                "From": "+919876543210",
                "SpeechResult": "gehun",
                "Confidence": "0.85",
            },
        )
        assert response.status_code == 200

    def test_gather_unrecognized_crop_retries(self, ivr_client):
        response = ivr_client.post(
            "/api/ivr/gather?state=uttar_pradesh",
            data={
                "CallSid": "gather-unrecog",
                "From": "+919876543210",
                "SpeechResult": "xyzabc123",
                "Confidence": "0.30",
            },
        )
        assert response.status_code == 200
        xml = response.text
        # Should contain retry message
        assert "समझ नहीं आया" in xml or "<Gather" in xml

    def test_gather_logs_call(self, ivr_client, ivr_call_log_memory):
        ivr_client.post(
            "/api/ivr/gather?state=uttar_pradesh",
            data={
                "CallSid": "gather-log-001",
                "From": "+919876543210",
                "SpeechResult": "wheat",
                "Confidence": "0.90",
            },
        )
        logs = [l for l in ivr_call_log_memory if l["call_id"] == "gather-log-001"]
        assert len(logs) >= 1

    def test_gather_with_price_lookup(self, ivr_client):
        """Test gather with crop that triggers price lookup."""
        response = ivr_client.post(
            "/api/ivr/gather?state=uttar_pradesh",
            data={
                "CallSid": "gather-price-001",
                "From": "+919876543210",
                "SpeechResult": "चावल",
                "Confidence": "0.92",
            },
        )
        assert response.status_code == 200
        # Response should be valid TwiML (either price response or error)
        assert "<?xml" in response.text


# ─── Audio Serving ──────────────────────────────────────────────

class TestIVRAudioServing:
    """Test audio file serving endpoint."""

    def test_audio_not_found(self, ivr_client):
        response = ivr_client.get("/api/ivr/audio/nonexistent-call-sid")
        assert response.status_code == 404

    def test_audio_served_from_cache(self, ivr_client, ivr_audio_cache):
        ivr_audio_cache["test-audio-001"] = b"fake-wav-data"
        response = ivr_client.get("/api/ivr/audio/test-audio-001")
        assert response.status_code == 200
        assert response.content == b"fake-wav-data"
        assert "audio/wav" in response.headers["content-type"]
        # Audio should be removed from cache after serving
        assert "test-audio-001" not in ivr_audio_cache


# ─── TTS Preview ────────────────────────────────────────────────

class TestIVRTTSPreview:
    """Test the TTS preview endpoint."""

    def test_tts_preview_requires_text(self, ivr_client):
        response = ivr_client.post("/api/ivr/tts", json={})
        assert response.status_code == 400

    @patch("backend.ivr.handler.sarvam_tts", return_value=b"fake-audio-bytes")
    def test_tts_preview_returns_audio(self, mock_tts, ivr_client):
        response = ivr_client.post("/api/ivr/tts", json={
            "text": "नमस्ते",
            "language": "hi-IN",
            "speaker": "priya",
        })
        assert response.status_code == 200
        assert "audio/wav" in response.headers["content-type"]

    @patch("backend.ivr.handler.sarvam_tts", return_value=None)
    def test_tts_preview_handles_failure(self, mock_tts, ivr_client):
        response = ivr_client.post("/api/ivr/tts", json={
            "text": "नमस्ते",
        })
        assert response.status_code == 502


# ─── Test Crop Lookup ───────────────────────────────────────────

class TestIVRTestCrop:
    """Test the crop lookup debug endpoint."""

    def test_test_crop_requires_crop(self, ivr_client):
        response = ivr_client.post("/api/ivr/test-crop", json={})
        assert response.status_code == 400

    @patch("backend.ivr.handler.fetch_crop_price")
    def test_test_crop_returns_prediction(self, mock_fetch, ivr_client):
        mock_fetch.return_value = {
            "crop": "wheat",
            "state": "uttar_pradesh",
            "current_price": 2150,
            "predicted_price_7d": 2180,
            "trend": "bullish",
        }
        response = ivr_client.post("/api/ivr/test-crop", json={
            "crop": "wheat",
            "state": "uttar_pradesh",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["crop"] == "wheat"
        assert "response_text_hindi" in data

    def test_test_crop_invalid_crop(self, ivr_client):
        response = ivr_client.post("/api/ivr/test-crop", json={
            "crop": "invalid_crop_xyz",
            "state": "uttar_pradesh",
        })
        assert response.status_code == 400

    def test_test_crop_invalid_state(self, ivr_client):
        response = ivr_client.post("/api/ivr/test-crop", json={
            "crop": "wheat",
            "state": "invalid_state",
        })
        assert response.status_code == 400


# ─── Call Stats ─────────────────────────────────────────────────

class TestIVRStats:
    """Test call statistics endpoint."""

    def test_stats_returns_empty(self, ivr_client, ivr_call_log_memory):
        response = ivr_client.get("/api/ivr/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 0

    def test_stats_after_calls(self, ivr_client, ivr_call_log_memory):
        # Make some calls
        for i in range(3):
            ivr_client.post("/api/ivr/incoming", data={
                "CallSid": f"stats-{i}",
                "From": "+919876543210",
                "To": "+911234567890",
                "Direction": "inbound",
            })
        response = ivr_client.get("/api/ivr/stats")
        data = response.json()
        assert data["total_calls"] >= 3

    def test_stats_filter_by_phone(self, ivr_client, ivr_call_log_memory):
        ivr_client.post("/api/ivr/incoming", data={
            "CallSid": "stats-phone-001",
            "From": "+919876543210",
            "To": "+911234567890",
            "Direction": "inbound",
        })
        response = ivr_client.get("/api/ivr/stats?phone=+919876543210")
        assert response.status_code == 200


# ─── Supported Crops ────────────────────────────────────────────

class TestIVRCrops:
    """Test supported crops list endpoint."""

    def test_crops_list(self, ivr_client):
        response = ivr_client.get("/api/ivr/crops")
        assert response.status_code == 200
        data = response.json()
        assert "crops" in data
        assert len(data["crops"]) >= 10

    def test_crops_have_hindi_names(self, ivr_client):
        response = ivr_client.get("/api/ivr/crops")
        crops = response.json()["crops"]
        hindi_crops = [c for c in crops if c["hindi"]]
        assert len(hindi_crops) >= 10

    def test_crops_have_voice_keywords(self, ivr_client):
        response = ivr_client.get("/api/ivr/crops")
        crops = response.json()["crops"]
        for crop in crops:
            assert len(crop["voice_keywords"]) >= 2


# ─── Health Check ───────────────────────────────────────────────

class TestIVRHealth:
    """Test IVR health endpoint."""

    def test_health(self, ivr_client):
        response = ivr_client.get("/api/ivr/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "exotel_configured" in data
        assert "sarvam_configured" in data


# ─── Outbound Call ──────────────────────────────────────────────

class TestIVROutboundCall:
    """Test outbound call initiation."""

    @patch("backend.ivr.handler.requests.post")
    def test_outbound_call_requires_phone(self, mock_post, ivr_client):
        response = ivr_client.post("/api/ivr/call", json={})
        assert response.status_code == 400

    @patch("backend.ivr.handler.EXOTEL_SID", "")
    def test_outbound_call_requires_exotel_config(self, ivr_client):
        response = ivr_client.post("/api/ivr/call", json={
            "phone": "+919876543210",
        })
        assert response.status_code == 503


# ─── Exotel Status Callback ─────────────────────────────────────

class TestIVRStatusCallback:
    """Test Exotel status callback."""

    def test_status_callback(self, ivr_client, ivr_call_log_memory):
        response = ivr_client.post("/api/ivr/status", data={
            "CallSid": "status-001",
            "CallStatus": "completed",
            "CallDuration": "45",
            "From": "+919876543210",
        })
        assert response.status_code == 200
        assert "OK" in response.text

    def test_status_callback_logs_call(self, ivr_client, ivr_call_log_memory):
        ivr_client.post("/api/ivr/status", data={
            "CallSid": "status-log-001",
            "CallStatus": "completed",
            "CallDuration": "30",
            "From": "+919876543210",
        })
        logs = [l for l in ivr_call_log_memory if l.get("status") == "call_completed"]
        assert len(logs) >= 1


# ─── Sarvam TTS Fallback ───────────────────────────────────────

class TestSarvamTTSFallback:
    """Test that gather falls back to <Say> when Sarvam TTS fails."""

    @patch("backend.ivr.handler.sarvam_tts", return_value=None)
    def test_gather_falls_back_to_say(self, mock_tts, ivr_client):
        response = ivr_client.post(
            "/api/ivr/gather?state=uttar_pradesh",
            data={
                "CallSid": "fallback-001",
                "From": "+919876543210",
                "SpeechResult": "wheat",
                "Confidence": "0.90",
            },
        )
        assert response.status_code == 200
        # Should contain <Say> instead of <Play>
        assert "<Say" in response.text

    @patch("backend.ivr.handler.sarvam_tts", return_value=b"audio-bytes")
    def test_gather_uses_play_with_tts(self, mock_tts, ivr_client, ivr_audio_cache):
        response = ivr_client.post(
            "/api/ivr/gather?state=uttar_pradesh",
            data={
                "CallSid": "tts-play-001",
                "From": "+919876543210",
                "SpeechResult": "wheat",
                "Confidence": "0.90",
            },
        )
        assert response.status_code == 200
        assert "<Play>" in response.text


# ─── Parametrized Crop Tests ───────────────────────────────────

@pytest.mark.parametrize("hindi,expected", [
    ("गेहूं", "wheat"),
    ("चावल", "rice"),
    ("मक्का", "maize"),
    ("कपास", "cotton"),
    ("सोयाबीन", "soybean"),
    ("आलू", "potato"),
    ("टमाटर", "tomato"),
    ("प्याज", "onion"),
    ("मूंगफली", "groundnut"),
    ("गन्ना", "sugarcane"),
])
def test_parametrized_hindi_crop_parsing(hindi, expected):
    from backend.ivr.handler import parse_crop_name
    assert parse_crop_name(hindi) == expected


@pytest.mark.parametrize("romanized,expected", [
    ("gehun", "wheat"),
    ("dhaan", "rice"),
    ("makka", "maize"),
    ("kapas", "cotton"),
    ("soyabean", "soybean"),
    ("aalo", "potato"),
    ("tamatar", "tomato"),
    ("pyaaz", "onion"),
    ("moongfali", "groundnut"),
    ("ganna", "sugarcane"),
])
def test_parametrized_romanized_crop_parsing(romanized, expected):
    from backend.ivr.handler import parse_crop_name
    assert parse_crop_name(romanized) == expected
