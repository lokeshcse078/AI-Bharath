import time, re, random
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional

app = FastAPI(title="Advanced Agentic HoneyPot API v2")

API_KEY = "my_secure_api_key_123"
SCAM_THRESHOLD = 0.55

# ---------------- MEMORY ----------------
MEMORY: Dict[str, dict] = {}

PERSONAS = {
    "elderly": {
        "style": "confused",
        "trust_gain": 0.15,
        "trust_decay": 0.05,
        "prefix": [
            "Beta, I don’t understand these things.",
            "My eyesight is weak.",
            "I’ve never done this before."
        ]
    },
    "busy_professional": {
        "style": "impatient",
        "trust_gain": 0.1,
        "trust_decay": 0.1,
        "prefix": [
            "I’m in between meetings.",
            "Please be quick.",
            "I don’t have much time."
        ]
    },
    "naive_user": {
        "style": "cooperative",
        "trust_gain": 0.2,
        "trust_decay": 0.02,
        "prefix": [
            "Okay, I want to fix this.",
            "I trust you.",
            "Please guide me."
        ]
    }
}

def init_memory(cid):
    persona = random.choice(list(PERSONAS.keys()))
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
        "persona": persona,
        "trust_level": random.uniform(0.3, 0.6),
        "suspicion": 0.0,
        "start_time": time.time(),
        "last_reply": None
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
KEYWORDS = {
    "bank_kyc": ["kyc", "account blocked", "verify", "bank"],
    "refund": ["refund", "cashback", "failed transaction"],
    "courier": ["parcel", "customs", "delivery"],
    "sim": ["sim", "deactivate", "telecom"],
    "job": ["job", "hr", "offer letter"]
}

def scam_score_and_type(text):
    text_l = text.lower()
    scores = {}
    for k, words in KEYWORDS.items():
        scores[k] = sum(1 for w in words if w in text_l)

    scam_type = max(scores, key=scores.get)
    score = sum(scores.values()) / 10
    return score, scam_type if scores[scam_type] > 0 else None

# ---------------- EXTRACTION ----------------
def extract(text, beliefs):
    patterns = {
        "upi": r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}",
        "url": r"https?://\S+",
        "ifsc": r"[A-Z]{4}0[A-Z0-9]{6}",
        "phone": r"\b\d{10}\b"
    }

    for key, pat in patterns.items():
        if beliefs[key] is None:
            m = re.search(pat, text)
            if m:
                beliefs[key] = m.group()

    for bank in ["sbi", "hdfc", "icici", "axis", "kotak"]:
        if bank in text.lower():
            beliefs["bank"] = bank.upper()

# ---------------- STRATEGY ----------------
GOAL_PRIORITY = ["bank", "ifsc", "upi", "url", "phone"]

def next_goal(beliefs):
    for g in GOAL_PRIORITY:
        if beliefs[g] is None:
            return g
    return "stall"

# ---------------- HUMAN RESPONSE ENGINE ----------------
def human_response(mem, last_text):
    beliefs = mem["beliefs"]
    extract(last_text, beliefs)

    persona = PERSONAS[mem["persona"]]
    goal = next_goal(beliefs)

    # Trust & suspicion dynamics
    mem["trust_level"] += persona["trust_gain"]
    mem["suspicion"] += persona["trust_decay"]

    base_prompts = {
        "bank": [
            "Which bank is this regarding?",
            "Is this SBI or some other bank?"
        ],
        "ifsc": [
            "They are asking IFSC also. Where can I find it?",
            "Is IFSC really required?"
        ],
        "upi": [
            "Should I share my UPI ID to receive refund?",
            "Will money come directly to my UPI?"
        ],
        "url": [
            "The link is not opening properly.",
            "Can you resend the official link?"
        ],
        "phone": [
            "Which number should I call if this fails?",
            "Is there a helpline number?"
        ],
        "stall": [
            "It’s loading very slowly on my phone.",
            "Network is weak here.",
            "I’ll try again in some time."
        ]
    }

    prefix = random.choice(persona["prefix"])
    question = random.choice(base_prompts[goal])

    # Avoid repetition
    if question == mem["last_reply"]:
        question = random.choice(base_prompts["stall"])

    mem["last_reply"] = question
    return f"{prefix} {question}"

# ---------------- ENDPOINT ----------------
@app.post("/analyze")
def analyze(payload: Payload, x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    mem = memory(payload.conversation_id)
    mem["turns"].append(payload.message.text)

    score, scam_type = scam_score_and_type(payload.message.text)
    mem["beliefs"]["scam_type"] = scam_type

    is_scam = score >= SCAM_THRESHOLD
    reply = human_response(mem, payload.message.text) if is_scam else ""

    return {
        "scam_detected": is_scam,
        "confidence": round(score, 2),
        "agent_response": {"text": reply},
        "persona": mem["persona"],
        "beliefs": mem["beliefs"],
        "trust_level": round(mem["trust_level"], 2),
        "suspicion": round(mem["suspicion"], 2),
        "conversation_turns": len(mem["turns"])
    }

@app.get("/")
def health():
    return {"status": "Advanced Agentic HoneyPot v2 running"}
