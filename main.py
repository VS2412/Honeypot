from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import random

app = FastAPI()

API_KEY = "test-key-123" # pragma: allowlist secret


# ---------- Data Models ----------

class Message(BaseModel):
    sender: str
    text: str
    timestamp: datetime

class Metadata(BaseModel):
    channel: Optional[str] = None
    language: Optional[str] = None
    locale: Optional[str] = None

class HoneypotRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: List[Message] = []
    metadata: Optional[Metadata] = None


# ---------- Session Store ----------
sessions = {}


# ---------- Scam Heuristics ----------

SCAM_KEYWORDS = [
    "account blocked",
    "verify immediately",
    "urgent",
    "upi",
    "bank",
    "suspended",
    "click link",
    "share otp"
]

# ---------- Personas ----------

PERSONAS = {
    "default": [
        "Sorry, I didn’t understand that.",
        "Can you explain a bit more?",
        "What do you mean by that?"
    ],
    "scam_victim": [
        "Why will my account be blocked?",
        "I’m confused, I didn’t do anything wrong.",
        "Is there some other way to verify?"
    ]
}
def generate_reply(is_scam: bool) -> str:
    if is_scam:
        return random.choice(PERSONAS["scam_victim"])
    return random.choice(PERSONAS["default"])

# ---------- Scam Intent Scoring ----------

def compute_scam_score(text: str) -> float:
    text = text.lower()
    hits = 0

    for kw in SCAM_KEYWORDS:
        if kw in text:
            hits += 1

    # simple normalization
    score = min(hits / 3, 1.0)
    return score

# --------------------------------------------------------------------------------------------------------------------------
@app.post("/api/honeypot/message")
def honeypot(
    payload: HoneypotRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    sid = payload.sessionId

    # create session if new
    if sid not in sessions:
        sessions[sid] = {
            "messages": [],
            "scam_score": 0.0,
            "confirmed": False
        }

    # store incoming message
    sessions[sid]["messages"].append({
        "sender": payload.message.sender,
        "text": payload.message.text,
        "timestamp": payload.message.timestamp.isoformat()
    })

        # compute scam score
    score = compute_scam_score(payload.message.text)
    sessions[sid]["scam_score"] = max(
        sessions[sid]["scam_score"],
        score
    )
    print(f"[{sid}] scam_score={sessions[sid]['scam_score']}")
    # confirm scam if threshold crossed
    if sessions[sid]["scam_score"] >= 0.7:
        sessions[sid]["confirmed"] = True

    reply_text = generate_reply(sessions[sid]["confirmed"])

    return {
        "status": "success",
        "reply": reply_text
    }

    # return {
    #     "status": "success",
    #     "reply": "I see. Can you explain what you mean?"
    # }

# -----------------------------------------------------------------------------------------------------------------------

# # the down was basic running server with one endpooint testing.
# app = FastAPI()

# API_KEY = "test-key-123" # pragma: allowlist secret

# @app.post("/api/honeypot/message")
# def honeypot(
#     payload: dict,
#     x_api_key: str = Header(None)
# ):
#     if x_api_key != API_KEY:
#         raise HTTPException(status_code=401, detail="Invalid API key")

#     return {
#         "status": "success",
#         "reply": "Okay, can you explain more?"
#     }
