import time, re, random
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

app = FastAPI(title="Advanced Agentic HoneyPot API")

API_KEY = "my_secure_api_key_123"

# ---------------- MEMORY ----------------
MEMORY: Dict[str, dict] = {}

def init_memory(cid):
    MEMORY[cid] = {
        "beliefs": {
            "bank": None,
            "upi": None,
            "ifsc": None,
            "url": None,
            "phone": None,
            "scam_type": None
        },
        "turns": [],
        "persona": random.choice(["elderly", "busy_professional", "naive_user"]),
        "suspicion_level": 0.0,
        "start_time": time.time()
    }

def memory(cid):
    if cid not in MEMORY:
        init_memory(cid)
    return MEMORY[cid]

# ---------------- MODELS ----------------
class Message(BaseModel):
    sender: str
    text: str

class Payload(BaseModel):
    conversation_id: str
    event_id: str
    timestamp: str
    message: Message

# ---------------- SCAM DETECTION ----------------
KEYWORDS = [
    "verify", "blocked", "refund", "urgent",
    "upi", "click", "link", "account", "kyc"
]

def scam_score(text):
    hits = sum(1 for k in KEYWORDS if k in text.lower())
    return hits / len(KEYWORDS)

# ---------------- INTELLIGENCE EXTRACTION ----------------
def extract(text, beliefs):
    if not beliefs["upi"]:
        m = re.search(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text)
        if m: beliefs["upi"] = m.group()

    if not beliefs["url"]:
        m = re.search(r"https?://\S+", text)
        if m: beliefs["url"] = m.group()

    if not beliefs["ifsc"]:
        m = re.search(r"[A-Z]{4}0[A-Z0-9]{6}", text)
        if m: beliefs["ifsc"] = m.group()

    if not beliefs["phone"]:
        m = re.search(r"\b\d{10}\b", text)
        if m: beliefs["phone"] = m.group()

    for bank in ["sbi", "hdfc", "icici", "axis", "kotak"]:
        if bank in text.lower():
            beliefs["bank"] = bank.upper()

# ---------------- PERSONA LANGUAGE ----------------
PERSONA_TEMPLATES = {
    "elderly": [
        "Beta, I’m not very good with phone.",
        "My son usually does this.",
        "Please explain slowly."
    ],
    "busy_professional": [
        "I’m in a meeting right now.",
        "Can you make this quick?",
        "I don’t have much time."
    ],
    "naive_user": [
        "Okay, I want to fix this.",
        "I don’t know much about this.",
        "Just tell me what to do."
    ]
}

# ---------------- STRATEGIC PLANNER ----------------
def next_goal(beliefs):
    for k, v in beliefs.items():
        if v is None:
            return k
    return "stall"

# ---------------- HUMAN-LIKE RESPONSE ENGINE ----------------
def respond(mem, last_text):
    beliefs = mem["beliefs"]
    extract(last_text, beliefs)

    goal = next_goal(beliefs)
    persona = mem["persona"]
    prefix = random.choice(PERSONA_TEMPLATES[persona])

    prompts = {
        "bank": "Which bank is this regarding?",
        "ifsc": "They are asking IFSC also. What is it?",
        "upi": "Should I share my UPI ID for refund?",
        "url": "Please send the official link again.",
        "phone": "Which number should I call if this fails?",
        "stall": "It’s loading very slowly on my phone."
    }

    return f"{prefix} {prompts[goal]}"

# ---------------- ENDPOINT ----------------
@app.post("/analyze")
def analyze(payload: Payload, x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    mem = memory(payload.conversation_id)
    mem["turns"].append(payload.message.text)

    score = scam_score(payload.message.text)
    is_scam = score > 0.55

    reply = ""
    if is_scam:
        reply = respond(mem, payload.message.text)

    return {
        "scam_detected": is_scam,
        "confidence": round(score, 2),
        "agent_response": {"text": reply},
        "beliefs": mem["beliefs"],
        "persona": mem["persona"],
        "conversation_turns": len(mem["turns"])
    }

@app.get("/")
def health():
    return {"status": "Advanced Agentic HoneyPot running"}
