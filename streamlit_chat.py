"""Streamlit chat frontend for DEUS Bank AI Support System."""

import uuid
import requests
import streamlit as st

API_URL = "http://localhost:8000/chat"

st.set_page_config(page_title="DEUS Bank Support", page_icon="🏦", layout="centered")

# ── Session state init ─────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "current_agent" not in st.session_state:
    st.session_state.current_agent = "greeter"
if "conversation_ended" not in st.session_state:
    st.session_state.conversation_ended = False

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏦 DEUS Bank")
    st.divider()

    st.markdown("**Session**")
    st.code(st.session_state.session_id[:8] + "...", language=None)

    st.markdown("**Status**")
    auth_label = "✅ Authenticated" if st.session_state.is_authenticated else "🔒 Not authenticated"
    st.markdown(auth_label)
    st.markdown(f"Agent: `{st.session_state.current_agent}`")

    st.divider()
    st.markdown("**Test credentials**")
    st.markdown("""
| User | Tier | Fields to provide |
|------|------|-------------------|
| Lisa | Premium | name + phone |
| John | Standard | name + IBAN |
| Maria | Standard | phone + IBAN |

**Lisa**
- Name: `Lisa`
- Phone: `+1122334455`
- IBAN: `DE89370400440532013000`
- Secret answer: `Yoda`

**John**
- Name: `John`
- Phone: `+1987654321`
- IBAN: `GB29NWBK60161331926819`
- Secret answer: `Smith`

**Maria**
- Name: `Maria`
- Phone: `+1555000111`
- IBAN: `FR7630006000011234567890189`
- Secret answer: `Fluffy`
""")

    st.divider()
    if st.button("🔄 New session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.is_authenticated = False
        st.session_state.current_agent = "greeter"
        st.session_state.conversation_ended = False
        st.rerun()

# ── Main chat area ─────────────────────────────────────────────
st.title("DEUS Bank Support")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.conversation_ended:
    st.info("This conversation has ended. Click **New session** in the sidebar to start over.")
    st.stop()

if prompt := st.chat_input("Type your message…"):
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API
    with st.chat_message("assistant"):
        with st.spinner(""):
            try:
                resp = requests.post(
                    API_URL,
                    json={"session_id": st.session_state.session_id, "message": prompt},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()

                reply = data["response"]
                st.session_state.is_authenticated = data.get("is_authenticated", False)
                st.session_state.current_agent = data.get("current_agent", "greeter")
                st.session_state.conversation_ended = data.get("conversation_ended", False)

            except requests.exceptions.ConnectionError:
                reply = "⚠️ Cannot reach the API at localhost:8000. Is `docker compose up` running?"
            except Exception as e:
                reply = f"⚠️ Error: {e}"

        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    st.rerun()
