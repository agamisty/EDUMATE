import uuid
from datetime import datetime
import streamlit as st

def chat_message_ui(chat, is_user=True):
    with st.chat_message("user" if is_user else "assistant"):
        st.markdown(
            f"{'👤' if is_user else '🤖'} {chat['message']}", unsafe_allow_html=True
        )
        st.markdown(f"<small>{chat['timestamp']}</small>", unsafe_allow_html=True)

        cols = st.columns([0.1, 0.1, 0.1])
        with cols[0]:
            if st.button("✏️", key=f"edit-{chat['id']}-{is_user}", help="Edit this message"):
                st.session_state["edit_mode"] = chat["id"]
                st.toast("", icon="✏️")
        with cols[1]:
            if st.button("📋", key=f"copy-{chat['id']}-{is_user}", help="Copy this message"):
                st.code(chat["message"], language="markdown")
                st.toast("", icon="📋")
        with cols[2]:
            if st.button("📌", key=f"pin-{chat['id']}-{is_user}", help="Pin this chat"):
                st.session_state["pin_chat"] = chat["id"]
                st.toast("", icon="📌")


def sidebar_chat_history_ui(chat_list):  # sourcery skip: use-named-expression
    st.sidebar.subheader("📚 Chat History")

    # 🔍 Search bar
    search_query = st.sidebar.text_input("Search chats...", key="search_chats")
    filtered_chats = [
        c for c in chat_list if search_query.lower() in c["title"].lower()
    ] if search_query else chat_list

    seen_ids = set()
    pinned_chats = [c for c in filtered_chats if c.get("pinned") and c["id"] not in seen_ids and not seen_ids.add(c["id"])]
    if pinned_chats:
        st.sidebar.subheader("📌 Pinned")
        for chat in pinned_chats:
            render_chat_item(chat)

    recent_chats = [c for c in filtered_chats if not c.get("pinned") and c["id"] not in seen_ids and not seen_ids.add(c["id"])]
    if recent_chats:
        st.sidebar.subheader("⏱️ Recent")
        for chat in recent_chats:
            render_chat_item(chat)

    st.sidebar.markdown("---")


def render_chat_item(chat):
    cols = st.sidebar.columns([0.7, 0.15, 0.15])
    with cols[0]:
        if st.button(f"💬 {chat['title']}", key=f"load-{chat['id']}"):
            st.session_state["active_chat_id"] = chat["id"]
            st.toast("Chat loaded!", icon="📂")
    with cols[1]:
        if st.button("📌", key=f"sidebar-pin-{chat['id']}"):
            st.session_state["pin_chat"] = chat["id"]
    with cols[2]:
        if st.button("⋮", key=f"menu-{chat['id']}"):
            st.session_state["show_menu_for"] = chat["id"]
    
    if st.session_state.get("show_menu_for") == chat["id"]:
        with st.expander("Chat Options", expanded=True):
            st.markdown("<div style='font-size: 0.9em;'>", unsafe_allow_html=True)
            if st.button("✏️ Edit Chat Title", key=f"edit-title-{chat['id']}", help="Edit the title of this chat"):
                st.session_state["edit_title_for"] = chat["id"]
                st.session_state["show_menu_for"] = None
                st.toast("Edit mode enabled!", icon="✏️")
            if st.button("🗑️ Delete Chat", key=f"delete-chat-{chat['id']}", help="Delete this chat"):
                st.session_state["delete_chat"] = chat["id"]
                st.session_state["show_menu_for"] = None
                st.toast("Chat deleted!", icon="🗑️")
            if st.button("📌 Pin/Unpin", key=f"pin-chat-{chat['id']}", help="Pin or unpin this chat"):
                st.session_state["pin_chat"] = chat["id"]
                st.session_state["show_menu_for"] = None
                st.toast("Pin toggled!", icon="📌")
            if st.button("✕ Close", key=f"close-modal-{chat['id']}", help="Close this menu"):
                st.session_state["show_menu_for"] = None
            st.markdown("</div>", unsafe_allow_html=True)


def user_input_ui(pause_key="pause"):
    col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
    with col1:
        user_input = st.text_input(
            "Ask or type...", key="user_input", label_visibility="collapsed"
        )
    with col2:
        if st.button("📎", key="attach", help="Attach a file"):
            st.session_state["attach_mode"] = True
    with col3:
        paused = st.session_state.get("paused", False)
        if st.button("⏸️" if not paused else "▶️", key=pause_key, help="Pause" if not paused else "Resume"):
            st.session_state["paused"] = not paused
            st.toast("Paused!" if not paused else "Resumed!", icon="⏸️" if not paused else "▶️")
            st.experimental_rerun()
    return user_input
