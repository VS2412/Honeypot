# the down was basic running server with one endpooint testing.
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()

API_KEY = "test-key-123" # pragma: allowlist secret

@app.post("/api/honeypot/message")
def honeypot(
    payload: dict,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return {
        "status": "success",
        "reply": "Okay, can you explain more?"
    }
