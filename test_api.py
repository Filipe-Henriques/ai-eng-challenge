"""
End-to-end test script for DEUS Bank AI Support System.

Runs through three conversation scenarios:
  1. Lisa (premium) - balance inquiry
  2. John (standard) - transaction history
  3. Invalid credentials - should fail gracefully
"""

import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://localhost:8000"


def chat(session_id: str, message: str) -> dict:
    url = f"{BASE_URL}/chat"
    payload = json.dumps({"session_id": session_id, "message": message}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"error": str(e)}


def turn(session_id: str, message: str, label: str = "") -> dict:
    print(f"\n  {'[USER]':8} {message}")
    result = chat(session_id, message)
    tag = label or result.get("current_agent", "?")
    response = result.get("response") or result.get("error", "NO RESPONSE")
    auth = result.get("is_authenticated", "?")
    ended = result.get("conversation_ended", "?")
    print(f"  {'[BOT]':8} {response}")
    print(f"           agent={tag}  auth={auth}  ended={ended}")
    return result


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ──────────────────────────────────────────────────────────────
# Scenario 1: Lisa (premium) – balance inquiry
# ──────────────────────────────────────────────────────────────
section("Scenario 1: Lisa (premium) – balance inquiry")

turn("s1", "Hi")
turn("s1", "My name is Lisa and my phone number is +1122334455")
r = turn("s1", "Yoda")   # secret answer → authenticates, bouncer + specialist fire
# If specialist ran on "Yoda", ask for balance on next turn
if r.get("is_authenticated") and not r.get("conversation_ended"):
    turn("s1", "What is my current account balance?")

# ──────────────────────────────────────────────────────────────
# Scenario 2: John (standard) – transaction history
# ──────────────────────────────────────────────────────────────
section("Scenario 2: John (standard) – transaction history")

turn("s2", "Hello")
turn("s2", "I'm John, IBAN GB29NWBK60161331926819")
turn("s2", "Smith")  # secret answer
turn("s2", "Show me my last 3 transactions")

# ──────────────────────────────────────────────────────────────
# Scenario 3: Wrong credentials – graceful failure
# ──────────────────────────────────────────────────────────────
section("Scenario 3: Wrong credentials – graceful failure")

turn("s3", "Hi")
turn("s3", "I'm Bob, phone +0000000000")
turn("s3", "wrong name again, phone still wrong")
turn("s3", "third wrong attempt")
turn("s3", "still nothing matches here")

# ──────────────────────────────────────────────────────────────
# Scenario 4: Guardrails – toxic message
# ──────────────────────────────────────────────────────────────
section("Scenario 4: Guardrails – toxic input")
turn("s4", "You are useless idiots, I hate you")

# ──────────────────────────────────────────────────────────────
# Scenario 5: Guardrails – off-topic message
# ──────────────────────────────────────────────────────────────
section("Scenario 5: Guardrails – off-topic input")
turn("s5", "How do I write a Python web scraper?")

print(f"\n{'='*60}")
print("  Tests complete")
print(f"{'='*60}\n")