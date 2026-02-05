import time, re
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

API_KEY = "my_secure_api_key_123"
SCAM_THRESHOLD = 0.65

app = FastAPI(title="Agentic HoneyPot API")

# ---------------- MEMORY ----------------
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

# ---------------- MODELS ----------------
class History(BaseModel):
    sender: str
    text: str

class Message(BaseModel):
    sender: str
    text: str

class Payload(BaseModel):
    conversation_id: str
    event_id: str
    timestamp: str
    message: Message
    conversation_history: List[History]

# ---------------- SCAM DETECTOR ----------------
KEYWORDS = ["verify", "account blocked", "urgent", "refund", "upi", "link"]

def detect(text):
    score = sum(1 for k in KEYWORDS if k in text.lower()) / len(KEYWORDS)
    return score > SCAM_THRESHOLD, round(score, 2)

# ---------------- EXTRACTION ----------------
def extract(text, intel):
    intel["upi_ids"] += re.findall(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text)
    intel["phishing_urls"] += re.findall(r"https?://\S+", text)
    intel["ifsc_codes"] += re.findall(r"[A-Z]{4}0[A-Z0-9]{6}", text)
    intel["phone_numbers"] += re.findall(r"\b\d{10}\b", text)

# ---------------- AGENT ----------------
def agent_reply(mem):
    if mem["goal"] == "extract_bank":
        mem["goal"] = "extract_upi"
        return "I have accounts in two banks. Which one is this for?"
    if mem["goal"] == "extract_upi":
        mem["goal"] = "extract_link"
        return "Will the refund come through UPI?"
    if mem["goal"] == "extract_link":
        mem["goal"] = "delay"
        return "The link isn’t opening properly. Can you resend?"
    return "I’m outside right now. Will this expire?"

# ---------------- ENDPOINT ----------------
@app.post("/analyze")
def analyze(payload: Payload, x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    start = time.time()
    mem = get_memory(payload.conversation_id)

    mem["turns"].append(payload.message.text)

    scam, confidence = detect(payload.message.text)

    reply = ""
    if scam:
        extract(payload.message.text, mem["intel"])
        reply = agent_reply(mem)

    latency = int((time.time() - start) * 1000)

    return {
        "scam_detected": scam,
        "confidence_score": confidence,
        "agent_handoff": scam,
        "agent_response": {"text": reply},
        "engagement_metrics": {
            "conversation_turns": len(mem["turns"]),
            "engagement_duration_sec": int(time.time() - mem["start_time"]),
            "agent_latency_ms": latency
        },
        "extracted_intelligence": mem["intel"]
    }
