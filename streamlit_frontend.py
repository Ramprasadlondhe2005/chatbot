import streamlit as st
import time
import uuid
from langgraph_backend import stream_ai_response, load_chat_history, save_chat_message, get_user_chats
from datetime import datetime

st.set_page_config(page_title="LangGraph Chatbot", layout="wide")
st.title("🤖 LangGraph Chatbot with MongoDB")

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user_{uuid.uuid4().hex[:8]}"

if "chats" not in st.session_state:
    st.session_state.chats = {}

if "current_chat" not in st.session_state:
    # Check if user has existing chats
    existing_chats = get_user_chats(st.session_state.user_id)
    if existing_chats:
        # Load first chat
        st.session_state.current_chat = existing_chats[0]["thread_id"]
        # Load its messages
        st.session_state.chats[st.session_state.current_chat] = load_chat_history(st.session_state.current_chat)
    else:
        # Create new chat
        new_id = str(uuid.uuid4())
        st.session_state.current_chat = new_id
        st.session_state.chats[new_id] = []

# ================= SIDEBAR =================
with st.sidebar:
    st.header("💬 My Conversations")
    st.caption(f"User ID: {st.session_state.user_id[:8]}...")
    
    # -------- NEW CHAT BUTTON --------
    if st.button("➕ New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.current_chat = new_id
        st.session_state.chats[new_id] = []
        st.rerun()
    
    st.divider()
    
    # -------- REFRESH CHAT LIST --------
    if st.button("🔄 Refresh Chats", use_container_width=True):
        st.rerun()
    
    # -------- CHAT LIST --------
    # Get updated chat list from MongoDB
    chat_list = get_user_chats(st.session_state.user_id)
    
    if not chat_list:
        st.info("No chats yet. Start a new conversation!")
    
    for chat in chat_list:
        # Create a button for each chat
        chat_preview = chat["preview"] if chat["preview"] else "Empty chat"
        time_ago = chat["updated_at"].strftime("%H:%M %d/%m") if isinstance(chat["updated_at"], datetime) else "Recent"
        
        button_label = f"📝 {chat_preview}\n🕐 {time_ago} ({chat['message_count']} msgs)"
        
        if st.button(button_label, key=chat["thread_id"], use_container_width=True):
            st.session_state.current_chat = chat["thread_id"]
            # Load this chat's messages
            st.session_state.chats[chat["thread_id"]] = load_chat_history(chat["thread_id"])
            st.rerun()
    
    st.divider()
    
    # -------- DELETE CURRENT CHAT --------
    if st.button("🗑️ Delete Current Chat", use_container_width=True, type="primary"):
        if st.session_state.current_chat in st.session_state.chats:
            del st.session_state.chats[st.session_state.current_chat]
            # Create new chat
            new_id = str(uuid.uuid4())
            st.session_state.current_chat = new_id
            st.session_state.chats[new_id] = []
            st.rerun()

# ================= MAIN CHAT AREA =================
st.header(f"💬 Chat Session: {st.session_state.current_chat[:8]}")

# Get current chat messages
if st.session_state.current_chat not in st.session_state.chats:
    st.session_state.chats[st.session_state.current_chat] = load_chat_history(st.session_state.current_chat)

messages = st.session_state.chats[st.session_state.current_chat]

# -------- DISPLAY OLD MESSAGES --------
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ================= CHAT INPUT =================
user_input = st.chat_input("Type your message...")

if user_input:
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Save user message to MongoDB
    save_chat_message(
        thread_id=st.session_state.current_chat,
        role="user",
        content=user_input,
        user_id=st.session_state.user_id
    )
    
    # Add to session state
    st.session_state.chats[st.session_state.current_chat].append({
        "role": "user",
        "content": user_input
    })
    
    # -------- STREAMING RESPONSE --------
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Stream the response
        for token in stream_ai_response(user_input, st.session_state.current_chat):
            full_response += token
            message_placeholder.markdown(full_response + "▌")
            time.sleep(0.01)
        
        message_placeholder.markdown(full_response)
    
    # Save assistant message to MongoDB
    save_chat_message(
        thread_id=st.session_state.current_chat,
        role="assistant",
        content=full_response,
        user_id=st.session_state.user_id
    )
    
    # Add to session state
    st.session_state.chats[st.session_state.current_chat].append({
        "role": "assistant",
        "content": full_response
    })

# ================= FOOTER =================
st.divider()
st.caption("💾 All messages are automatically saved to MongoDB")