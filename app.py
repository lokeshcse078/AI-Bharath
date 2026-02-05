import streamlit as st
import json
import time
import re

# ---------------- CONFIG ----------------
API_KEY = "CHANGE_THIS_API_KEY"
SCAM_THRESHOLD = 0.65

# ---------------- MEMORY ----------------
if "MEMORY_STORE" not in st.session_state:
    st.session_state.MEMORY_STORE = {}

def get_memory(conversation_id):
    if conversation_id not in st.session_state.MEMORY_STORE:
        st.session_state.MEMORY_STORE[conversation_id] = {
            "turns": [],
            "extracted_intelligence": {
                "upi_ids": [],
                "bank_accounts": [],
                "ifsc_codes": [],
                "phishing_urls": [],
                "phone_numbers": []
            },
            "strategy_state": {
                "next_goal": "extract_bank"
            }
        }
    return st.session_state.MEMORY_STORE[conversation_id]

# ---------------- DETECTOR ----------------
SCAM_KEYWORDS = [
    "account blocked", "verify", "urgent",
    "click", "refund", "upi", "bank", "link"
]

def detect_scam(text):
    text = text.lower()
    hits = sum(1 for k in SCAM_KEYWORDS if k in text)
    rule_score = hits / len(SCAM_KEYWORDS)
    llm_stub_score = 0.9 if "verify" in text else 0.4
    final_score = 0.6 * rule_score + 0.4 * llm_stub_score
    return final_score > SCAM_THRESHOLD, round(final_score, 2)

# ---------------- EXTRACTION ----------------
UPI_REGEX = r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}"
URL_REGEX = r"https?://[^\s]+"
IFSC_REGEX = r"[A-Z]{4}0[A-Z0-9]{6}"
PHONE_REGEX = r"\b\d{10}\b"

def extract_intelligence(text, intel):
    intel["upi_ids"] += re.findall(UPI_REGEX, text)
    intel["phishing_urls"] += re.findall(URL_REGEX, text)
    intel["ifsc_codes"] += re.findall(IFSC_REGEX, text)
    intel["phone_numbers"] += re.findall(PHONE_REGEX, text)

# ---------------- AGENT ----------------
def generate_agent_reply(memory):
    goal = memory["strategy_state"]["next_goal"]

    if goal == "extract_bank":
        memory["strategy_state"]["next_goal"] = "extract_upi"
        return "Which bank is this related to? I have two accounts."

    if goal == "extract_upi":
        memory["strategy_state"]["next_goal"] = "extract_link"
        return "The refund will come to my UPI ID right?"

    if goal == "extract_link":
        memory["strategy_state"]["next_goal"] = "delay"
        return "The link didn’t open properly. Can you resend it?"

    return "I’m currently outside. Will this expire soon?"

# ---------------- API HANDLER ----------------
def handle_request(payload):
    start = time.time()

    conversation_id = payload["conversation_id"]
    message_text = payload["message"]["text"]

    memory = get_memory(conversation_id)
    memory["turns"].append({"role": "scammer", "text": message_text})

    scam_detected, confidence = detect_scam(message_text)

    agent_text = ""
    if scam_detected:
        extract_intelligence(message_text, memory["extracted_intelligence"])
        agent_text = generate_agent_reply(memory)
        memory["turns"].append({"role": "agent", "text": agent_text})

    latency = int((time.time() - start) * 1000)

    return {
        "scam_detected": scam_detected,
        "confidence_score": confidence,
        "agent_handoff": scam_detected,
        "agent_response": {"text": agent_text},
        "engagement_metrics": {
            "conversation_turns": len(memory["turns"]),
            "engagement_duration_sec": len(memory["turns"]) * 10,
            "agent_latency_ms": latency
        },
        "extracted_intelligence": memory["extracted_intelligence"],
        "memory_update": {
            "scammer_profile": {
                "intent": "bank_phishing" if scam_detected else "unknown"
            }
        }
    }

# ---------------- STREAMLIT ENTRY ----------------
st.set_page_config(pageTitle="Agentic HoneyPot API")

params = st.query_params

if "api" in params:
    try:
        payload = json.loads(params["payload"])
        response = handle_request(payload)
        st.json(response)
    except Exception as e:
        st.json({"error": str(e)})

else:
    st.title("🕵️ Agentic Honey-Pot (Streamlit Public Endpoint)")
    st.markdown("""
### API Usage

Example payload:
```json
{
  "conversation_id": "conv_1",
  "message": {
    "text": "Your bank account is blocked. Verify now."
  }
}
""")

