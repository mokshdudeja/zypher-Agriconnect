"""
AgriConnect — Sarvam Voice Agents Integration

Provides instant outbound calling to farmers using Sarvam's programmable
voice-AI agents. Farmers without smartphones can interact with the platform
via natural phone conversations in Hindi/English.

APIs used:
- POST /outbounds/v1/.../outbounds — trigger instant outbound call
- POST webhook — receive call outcomes, transcripts, extracted data

Docs: https://docs.sarvam.ai/conversations/deploy/deploy-with-code
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

import requests
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────────

app = FastAPI(
    title="AgriConnect Voice Agents",
    description="Sarvam Voice Agents integration for farmer phone calls",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ──────────────────────────────────────────────────────

SARVAM_VA_API_KEY = os.getenv("SARVAM_VA_API_KEY", "sk_samvaad_er9gqrus_nu26TjSwDYQh6ZjMxwLbsLnt")
SARVAM_VA_BASE = "https://apps.sarvam.ai/api"

ORG_ID = os.getenv("SARVAM_ORG_ID", "01a046f3-1214-722c-b409-6b83b7889c3b")
WORKSPACE_ID = os.getenv("SARVAM_WORKSPACE_ID", "01a046f3-1219-75f8-8b92-2ad1028ae7f8")

# Agent config — fill in after creating agent in Sarvam UI
AGENT_APP_ID = os.getenv("SARVAM_AGENT_APP_ID", "agriconnect-farmer-agent")
AGENT_APP_VERSION = int(os.getenv("SARVAM_AGENT_VERSION", "1"))
CONNECTION_ID = os.getenv("SARVAM_CONNECTION_ID", "Exotel-Moks-136886e1-8df5")
AGENT_PHONE = os.getenv("SARVAM_AGENT_PHONE", "+911141183996")

# Webhook URL — Sarvam POSTs call outcomes here
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev")


# ─── In-Memory Call Log (replace with DynamoDB in production) ─────

_call_log: List[Dict[str, Any]] = []


# ─── Models ──────────────────────────────────────────────────────

class OutboundCallRequest(BaseModel):
    """Request body to trigger an instant outbound call to a farmer."""
    farmer_phone: str = Field(..., description="Farmer's phone number in E.164 format (e.g. +919876543210)")
    farmer_name: Optional[str] = Field(None, description="Farmer's name for personalization")
    state: Optional[str] = Field(None, description="Farmer's state for localized response")
    crop_name: Optional[str] = Field(None, description="Specific crop to discuss (optional)")
    language: Optional[str] = Field("Hindi", description="Conversation language")
    webhook_metadata: Optional[Dict[str, Any]] = Field(None, description="Custom metadata for webhook correlation")


class OutboundCallResponse(BaseModel):
    """Response after triggering an outbound call."""
    attempt_id: str
    status: str = "initiated"
    farmer_phone: str
    message: str


class CallLogEntry(BaseModel):
    """A single call log record."""
    attempt_id: str
    farmer_phone: str
    farmer_name: Optional[str]
    status: str
    duration: Optional[float]
    interaction_id: Optional[str]
    failure_reason: Optional[str]
    transcript: Optional[List[Dict[str, str]]]
    agent_variables: Optional[Dict[str, Any]]
    created_at: str
    webhook_metadata: Optional[Dict[str, Any]]


# ─── Voice Agents API Client ─────────────────────────────────────

def _va_headers():
    """Headers for Sarvam Voice Agents API."""
    return {
        "Content-Type": "application/json",
        "X-API-Key": SARVAM_VA_API_KEY,
    }


def trigger_outbound_call(
    farmer_phone: str,
    farmer_name: Optional[str] = None,
    state: Optional[str] = None,
    crop_name: Optional[str] = None,
    language: str = "Hindi",
    webhook_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Call the Sarvam Voice Agents instant outbound API.

    POST https://apps.sarvam.ai/api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds
    """
    url = f"{SARVAM_VA_BASE}/outbounds/v1/orgs/{ORG_ID}/workspaces/{WORKSPACE_ID}/outbounds"

    # Build agent variables — these get injected into the agent's prompt
    agent_variables = {}
    if farmer_name:
        agent_variables["farmer_name"] = farmer_name
    if state:
        agent_variables["state"] = state
    if crop_name:
        agent_variables["crop_name"] = crop_name

    payload = {
        "app_config": {
            "app_id": AGENT_APP_ID,
            "app_version": AGENT_APP_VERSION,
            "connection_config": {
                "connection_id": CONNECTION_ID,
                "agent_phone_number": AGENT_PHONE,
            },
        },
        "user_config": {
            "user_phone_number": farmer_phone,
        },
        "webhook_config": {
            "url": f"{WEBHOOK_BASE_URL}/api/voice-agents/webhook",
            "metadata": webhook_metadata or {},
        },
    }

    # Add optional fields
    if agent_variables:
        payload["app_config"]["agent_variables"] = agent_variables
    if language:
        payload["initial_language_name"] = language

    logger.info(f"Triggering outbound call to {farmer_phone} via Sarvam Voice Agents")
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

    resp = requests.post(url, json=payload, headers=_va_headers(), timeout=30)

    if resp.status_code not in (200, 201):
        logger.error(f"Sarvam VA API error: {resp.status_code} — {resp.text[:500]}")
        raise HTTPException(status_code=resp.status_code, detail=f"Sarvam API error: {resp.text[:300]}")

    return resp.json()


# ─── Endpoints ───────────────────────────────────────────────────

@app.post("/api/voice-agents/call", response_model=OutboundCallResponse)
async def make_call(req: OutboundCallRequest):
    """
    Trigger an instant outbound call to a farmer.

    The Sarvam Voice Agent will call the farmer's phone number and
    conduct a conversation about crop prices, weather, orders, etc.
    in Hindi/English.
    """
    try:
        result = trigger_outbound_call(
            farmer_phone=req.farmer_phone,
            farmer_name=req.farmer_name,
            state=req.state,
            crop_name=req.crop_name,
            language=req.language,
            webhook_metadata=req.webhook_metadata,
        )

        attempt_id = result.get("attempt_id", "unknown")

        # Log the call
        log_entry = {
            "attempt_id": attempt_id,
            "farmer_phone": req.farmer_phone,
            "farmer_name": req.farmer_name,
            "status": "initiated",
            "duration": None,
            "interaction_id": None,
            "failure_reason": None,
            "transcript": None,
            "agent_variables": None,
            "created_at": datetime.now().isoformat(),
            "webhook_metadata": req.webhook_metadata,
        }
        _call_log.insert(0, log_entry)

        return OutboundCallResponse(
            attempt_id=attempt_id,
            status="initiated",
            farmer_phone=req.farmer_phone,
            message=f"Call initiated to {req.farmer_phone}. Agent will connect shortly.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger call: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")


@app.post("/api/voice-agents/webhook")
async def voice_agent_webhook(request: Request):
    """
    Webhook endpoint for Sarvam Voice Agents call outcomes.

    Sarvam POSTs to this URL after each call attempt completes.
    Payload includes: attempt_id, status, duration, transcript,
    final_agent_variables, failure_reason.
    """
    try:
        payload = await request.json()
        logger.info(f"Voice Agent webhook received: status={payload.get('status')}")

        attempt_id = payload.get("attempt_id")
        status = payload.get("status")
        duration = payload.get("duration")
        interaction_id = payload.get("interaction_id")
        failure_reason = payload.get("failure_reason")
        agent_variables = payload.get("final_agent_variables")
        transcript = payload.get("interaction_transcript")
        webhook_metadata = payload.get("webhook_config", {}).get("metadata")

        # Update call log entry
        for entry in _call_log:
            if entry["attempt_id"] == attempt_id:
                entry["status"] = status
                entry["duration"] = duration
                entry["interaction_id"] = interaction_id
                entry["failure_reason"] = failure_reason
                entry["agent_variables"] = agent_variables
                entry["transcript"] = transcript
                break
        else:
            # Webhook arrived for a call we didn't initiate (e.g. inbound)
            _call_log.insert(0, {
                "attempt_id": attempt_id,
                "farmer_phone": payload.get("channel_info", {}).get("agent_phone_number", "unknown"),
                "farmer_name": agent_variables.get("farmer_name") if agent_variables else None,
                "status": status,
                "duration": duration,
                "interaction_id": interaction_id,
                "failure_reason": failure_reason,
                "transcript": transcript,
                "agent_variables": agent_variables,
                "created_at": datetime.now().isoformat(),
                "webhook_metadata": webhook_metadata,
            })

        # Log key info
        if status == "connected":
            logger.info(f"Call {attempt_id} connected — {duration}s — {len(transcript or [])} turns")
            if agent_variables:
                logger.info(f"Agent extracted: {json.dumps(agent_variables)}")
        else:
            logger.warning(f"Call {attempt_id} status={status} — reason={failure_reason}")

        return {"received": True, "attempt_id": attempt_id}

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"received": False, "error": str(e)}


@app.get("/api/voice-agents/calls")
async def list_calls(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status: connected, no_answer, busy, failed, initiated"),
):
    """List call history with optional status filter."""
    results = _call_log
    if status:
        results = [c for c in results if c["status"] == status]
    return {"calls": results[:limit], "total": len(results)}


@app.get("/api/voice-agents/calls/{attempt_id}")
async def get_call(attempt_id: str):
    """Get details for a specific call attempt."""
    for entry in _call_log:
        if entry["attempt_id"] == attempt_id:
            return entry
    raise HTTPException(status_code=404, detail="Call not found")


@app.get("/api/voice-agents/stats")
async def call_stats():
    """Get call statistics."""
    total = len(_call_log)
    connected = sum(1 for c in _call_log if c["status"] == "connected")
    failed = sum(1 for c in _call_log if c["status"] == "failed")
    no_answer = sum(1 for c in _call_log if c["status"] == "no_answer")
    busy = sum(1 for c in _call_log if c["status"] == "busy")
    initiated = sum(1 for c in _call_log if c["status"] == "initiated")

    avg_duration = 0
    connected_calls = [c for c in _call_log if c["duration"] is not None]
    if connected_calls:
        avg_duration = sum(c["duration"] for c in connected_calls) / len(connected_calls)

    return {
        "total": total,
        "connected": connected,
        "failed": failed,
        "no_answer": no_answer,
        "busy": busy,
        "initiated": initiated,
        "connection_rate": round(connected / total * 100, 1) if total > 0 else 0,
        "avg_duration_seconds": round(avg_duration, 1),
    }


@app.get("/api/voice-agents/health")
async def health():
    """Health check for Voice Agents integration."""
    return {
        "status": "ok",
        "api_key_configured": bool(SARVAM_VA_API_KEY),
        "org_id": ORG_ID,
        "workspace_id": WORKSPACE_ID,
        "agent_app_id": AGENT_APP_ID,
        "connection_id": CONNECTION_ID,
        "agent_phone": AGENT_PHONE,
        "webhook_url": f"{WEBHOOK_BASE_URL}/api/voice-agents/webhook",
    }
