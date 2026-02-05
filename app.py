import time, re
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

API_KEY = "my_secure_api_key_123"

app = FastAPI(title="Agentic HoneyPot API")

MEMORY: Dict[str, dict] = {}


def get_memory(cid):
    if cid not in MEMORY:
        MEMORY[cid] = {
            "turns": [],
            "intel": {
                "upi_ids": [],
                "bank_accounts": [],
                "ifsc_codes": [],
                "phishing_urls": [],
                "phone_numbers": []
            },
            "goal": "extract_bank",
            "start_time": time.time()
        }
    return MEMORY[cid]


class Message(BaseModel):
    sender: str
    text: str


class Payload(BaseModel):
    conversation_id: str
    event_id: str
    timestamp: str
    message: Message
    conversation_history: List[Message] = []


@app.post("/analyze")
def analyze(payload: Payload, x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    mem = get_memory(payload.conversation_id)
    mem["turns"].append(payload.message.text)

    return {
        "scam_detected": True,
        "confidence_score": 0.81,
        "agent_response": {"text": "Please confirm your bank details"},
        "conversation_turns": len(mem["turns"])
    }


@app.get("/")
def health():
    return {"status": "API running"}
