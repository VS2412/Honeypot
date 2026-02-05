from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import random
import re
import requests
import os
API_KEY = os.getenv("HONEYPOT_API_KEY", "test-key-123")  # pragma: allowlist secret

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

# ---------- Extraction Patterns ----------

UPI_PATTERN = r"\b[\w.-]+@[\w.-]+\b"
PHONE_PATTERN = r"\b(\+91[\s-]?)?\d{10}\b"
URL_PATTERN = r"https?://[^\s]+"
def extract_intelligence(text: str) -> dict:
    return {
        "upiIds": re.findall(UPI_PATTERN, text),
        "phoneNumbers": re.findall(PHONE_PATTERN, text),
        "phishingLinks": re.findall(URL_PATTERN, text)
    }
MAX_TURNS = 12
MIN_INTEL_FOR_EXIT = {
    "upiIds": 1,
    "phishingLinks": 1
}

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


# ---------- Mistral -------------------------------------------

def llm_agent_reply(session: dict) -> str:
    messages = session["messages"]

    convo = ""
    for m in messages[-6:]:  # last 6 messages only
        role = "Scammer" if m["sender"] == "scammer" else "You"
        convo += f"{role}: {m['text']}\n"

    STYLE_HINTS = [
        "Sound worried.",
        "Sound slightly angry.",
        "Sound confused.",
        "Sound rushed.",
        "Sound careless.",
        "Sound scared."
    ]

    style_hint = random.choice(STYLE_HINTS)

    system_prompt = (
        "You are a normal Indian user, not a professional.\n"
        "You are slightly stressed, impatient, and confused.\n"
        "You sometimes write incomplete sentences.\n"
        "You do NOT use formal language.\n"
        "You do NOT sound polite or professional.\n"
        "You may ask short questions or make worried statements.\n"
        "Do NOT mention scams, fraud, AI, or detection.\n"
        "Your goal is to get details like UPI IDs, links, or instructions.\n"
        "Vary your wording. Do NOT repeat sentence structures.\n"
        "One or two sentences max."
    )
    # system_prompt = (
    #     "You are a real human talking to a scammer.\n"
    #     "You are confused, cautious, and slightly worried.\n"
    #     "Do NOT reveal you detected a scam.\n"
    #     "Your goal is to get more details like UPI IDs, links, or instructions.\n"
    #     "Ask one short, natural question."
    # )
    prompt = (
        system_prompt
        + f"\nStyle hint: {style_hint}\n"
        + "Conversation:\n"
        + convo
        + "\nYou:"
    ) 
    # prompt = system_prompt + "\nConversation:\n" + convo + "\nYou:"
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            },
            timeout=10
        )
        return response.json()["response"].strip()
    except Exception:
        return generate_reply(True)


# ---------- Termination + AI taking some notes -------------------------------------------
def should_terminate(session: dict) -> bool:
    if len(session["messages"]) >= MAX_TURNS:
        return True

    intel = session["intelligence"]
    for key, count in MIN_INTEL_FOR_EXIT.items():
        if len(intel[key]) >= count:
            return True

    return False
def generate_agent_notes(session: dict) -> str:
    notes = []

    if session["intelligence"]["upiIds"]:
        notes.append("Scammer requested UPI-based transfer.")
    if session["intelligence"]["phishingLinks"]:
        notes.append("Scammer shared a phishing link.")
    if session["intelligence"]["phoneNumbers"]:
        notes.append("Scammer shared a contact number.")

    return " ".join(notes) if notes else "Scammer used social engineering tactics."


# ---------- GUVI Callback -------------------------------------------
def send_guvi_callback(session_id: str, session: dict):
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": len(session["messages"]),
        "extractedIntelligence": {
            "bankAccounts": [],  # , not implemented yet
            "upiIds": session["intelligence"]["upiIds"],
            "phishingLinks": session["intelligence"]["phishingLinks"],
            "phoneNumbers": session["intelligence"]["phoneNumbers"],
            "suspiciousKeywords": session["intelligence"]["suspiciousKeywords"]
        },
        "agentNotes": generate_agent_notes(session)
    }
    try:
        response = requests.post(
            "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
            json=payload,
            timeout=5
        )
        print("GUVI CALLBACK STATUS:", response.status_code)
    except Exception as e:
        print("GUVI CALLBACK ERROR:", str(e))



# --------------------------------------------------------------------------------------------------------------------------
@app.post("/api/honeypot/message")
def honeypot(
    payload: HoneypotRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    sid = payload.sessionId

    #create session if new
    if sid not in sessions:
        sessions[sid] = {
        "messages": [],
        "scam_score": 0.0,
        "confirmed": False,
        "terminated": False,
        "intelligence": {
        "upiIds": [],
        "phoneNumbers": [],
        "phishingLinks": [],
        "suspiciousKeywords": []
        }
    }
    # hydrate session from conversationHistory if session is new
    if sid not in sessions and payload.conversationHistory:
        sessions[sid]["messages"] = [
            {
                "sender": m.sender,
                "text": m.text,
                "timestamp": m.timestamp.isoformat()
            }
            for m in payload.conversationHistory
        ]

    #store incoming message
    sessions[sid]["messages"].append({
        "sender": payload.message.sender,
        "text": payload.message.text,
        "timestamp": payload.message.timestamp.isoformat()
    })

    #compute scam score
    score = compute_scam_score(payload.message.text)
    sessions[sid]["scam_score"] = max(
        sessions[sid]["scam_score"],
        score
    )
    print(f"[{sid}] scam_score={sessions[sid]['scam_score']}")

    #confirm scam if threshold crossed
    if sessions[sid]["scam_score"] >= 0.6:
        sessions[sid]["confirmed"] = True

    #AI / non-AI reply
    #reply_text = generate_reply(sessions[sid]["confirmed"])
    if sessions[sid]["confirmed"]:
        reply_text = llm_agent_reply(sessions[sid])
    else:
        reply_text = generate_reply(False)

    #extraction
    intel = extract_intelligence(payload.message.text)
    for key in ["upiIds", "phoneNumbers", "phishingLinks"]:
        sessions[sid]["intelligence"][key].extend(
            x for x in intel[key]
            if x not in sessions[sid]["intelligence"][key]
    )
    #track suspicious keywords
    for kw in SCAM_KEYWORDS:
        if kw in payload.message.text.lower():
            if kw not in sessions[sid]["intelligence"]["suspiciousKeywords"]:
                sessions[sid]["intelligence"]["suspiciousKeywords"].append(kw)
    print("INTELLIGENCE:", sessions[sid]["intelligence"])

    #termination check and sending the final result to GUVI 
    if sessions[sid]["confirmed"] and should_terminate(sessions[sid]) and not sessions[sid]["terminated"]:
        sessions[sid]["terminated"] = True
        print("TERMINATED = True")
        send_guvi_callback(sid, sessions[sid])

    #output 
    return {
        "status": "success",
        "reply": reply_text
    }
@app.get("/debug/session/{session_id}")
def debug_session(session_id: str):
    return sessions.get(session_id, {})


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

# this is required by render.
import os

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )