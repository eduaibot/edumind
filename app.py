import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uuid
import json
import sqlite3
import random
import re
import tempfile
from io import BytesIO
import matplotlib.pyplot as plt
from PIL import Image
import streamlit.components.v1 as components
import time

import hashlib

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()
    
    
def create_user(username, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                    (username, hash_password(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
              (username, hash_password(password)))
    data = c.fetchone()
    conn.close()
    return data

def inject_custom_ui():
    # 1. CSS cố định nút Dừng ở đáy màn hình
    st.markdown(
        """
        <style>
        div[data-testid="stButton"] button:has(div:contains("Dừng câu trả lời")) {
            position: fixed !important;
            bottom: 30px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: 80% !important;
            max-width: 700px !important;
            z-index: 999999 !important;
            background-color: #ff4b4b !important;
            color: black;
            border-radius: 10px !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
        }
        /* 1. Căn phải tin nhắn của User (Dựa vào việc có chứa icon 🐱) */
    div[data-testid="stChatMessage"]:has(div:contains("🐱")) {
        flex-direction: row-reverse; /* Đưa avatar sang bên phải */
    }
    
    div[data-testid="stChatMessage"]:has(div:contains("🐱")) > div:nth-child(2) {
        max-width: 50%; /* Giới hạn chiều rộng 50% */
        margin-left: auto; /* Đẩy khối chat sang phải */
        text-align: left; /* Chữ bên trong vẫn căn trái để dễ đọc */
        background-color: #f0f2f6; /* Đổi màu nền cho phân biệt (tuỳ chọn) */
        padding: 15px;
        border-radius: 15px;
    }

    /* 2. Cố định container chứa nút Dừng (Tránh bị đẩy lên) */
    .fixed-action-container {
        position: fixed;
        bottom: 3rem; /* Cách đáy một khoảng bằng chat_input */
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 730px; /* Chỉnh theo độ rộng layout của bạn */
        z-index: 9999;
        padding: 10px;
        background-color: white; /* Che lấp nội dung cuộn bên dưới */
    }
    
    /* Ẩn bớt khoảng trắng dư thừa do Streamlit tạo ra ở cuối trang */
    #end-of-chat { padding-bottom: 120px; }
    /* Nút dừng câu trả lời cố định ở đáy, thay thế vị trí thanh chat */
        .stop-container {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            max-width: 730px;
            z-index: 9999;
            padding: 0 20px;
        }
        .stButton > button[kind="primary"] { /* Giả lập style nút dừng */
            background-color: #ff4b4b !important;
            color: black;
            border-radius: 20px !important;
            height: 45px;
        }
        /* Căn phải cho User */
        div[data-testid="stChatMessage"]:has(div:contains("🐱")) {
            flex-direction: row-reverse;
        }
        div[data-testid="stChatMessage"]:has(div:contains("🐱")) > div:nth-child(2) {
            max-width: 70%;
            margin-left: auto;
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 15px;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
    # 2. JS tối ưu để tìm đúng khung cuộn (Scroll Container)
    components.html(
        """
        <script>
        const parentDoc = window.parent.document;
        function scrollToBottom() {
            // Tìm tất cả các vùng có khả năng cuộn trong Streamlit
            const selectors = [
                '.main .stVerticalBlock',
                'section.main',
                '.stAppViewMain',
                '.main'
            ];
            for (let s of selectors) {
                const el = parentDoc.querySelector(s);
                if (el && el.scrollHeight > el.clientHeight) {
                    el.scrollTo({
                        top: el.scrollHeight + 10000,
                        behavior: 'smooth'
                    });
                }
            }
        }
        // Tạo nút nếu chưa có
        
        </script>
        """,
        height=0,
    )
def scroll_to_bottom():
    # Đoạn Script này sẽ tìm vùng nội dung chính của Streamlit và kéo xuống cuối
    components.html(
        """
        <script>
            var scrollInterval = setInterval(function() {
                var mainPane = window.parent.document.querySelector('.main');
                if (mainPane) {
                    mainPane.scrollTo({ top: mainPane.scrollHeight, behavior: 'smooth' });
                    clearInterval(scrollInterval);
                }
            }, 100); // Thử lại sau mỗi 100ms cho đến khi tìm thấy
        </script>
        """,
        height=0,
    )
# Gọi CSS để hỗ trợ cuộn mượt
st.markdown(
    "<style> html { scroll-behavior: smooth; } </style>", unsafe_allow_html=True
)# --- CẤU HÌNH DATABASE VÀ KHỞI TẠO (GIỮ NGUYÊN) ---
DB_FILE = "edumind_history.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Bảng người dùng
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, 
                    password TEXT)""")
    
    # Bảng chats: Thêm cột username để phân biệt
    c.execute("""CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY, 
                    username TEXT, 
                    title TEXT, 
                    messages TEXT)""")
    
    c.execute("CREATE TABLE IF NOT EXISTS health_log (id TEXT, username TEXT, mood TEXT, note TEXT, date TEXT)")
    conn.commit()
    conn.close()


def save_chat_to_db(chat_id, username, title, messages):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO chats (id, username, title, messages) VALUES (?, ?, ?, ?)",
        (chat_id, username, title, json.dumps(messages)),
    )
    conn.commit()
    conn.close()
    
def load_all_chats_from_db(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Chỉ lấy chat có username trùng với người đang đăng nhập
    c.execute("SELECT id, title, messages FROM chats WHERE username = ?", (username,))
    rows = c.fetchall()
    conn.close()
    # Trả về dictionary để lưu vào session_state
    return {row[0]: {"title": row[1], "messages": json.loads(row[2])} for row in rows}

def delete_chat_from_db(chat_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Lỗi khi xoá database: {e}")
        return False
load_dotenv()
init_db()
st.set_page_config(page_title="EduMind AI", page_icon="🎓", layout="wide")
API_KEYS = []
for i in range(1, 4):
    k = os.getenv(f"GEMINI_API_KEY_{i}") or st.secrets.get(
        f"GEMINI_API_KEY_{i}")
    if k:
        API_KEYS.append(k)
if not API_KEYS:
    st.error("❌ Thiếu cấu hình API Key")
    st.stop()
MODELS_FAST = ["models/gemini-3-flash-preview", "models/gemini-2.5-flash"]
MODELS_THINKING = ["models/gemini-3.1-flash-lite-preview"]
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "all_chats" not in st.session_state:
    db_chats = load_all_chats_from_db()
    if db_chats:
        st.session_state.all_chats = db_chats
        st.session_state.current_chat_id = list(db_chats.keys())[-1]
    else:
        st.session_state.all_chats = {}
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {
            "title": "Trò chuyện mới", "messages": []}
        st.session_state.current_chat_id = new_id
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "key_index" not in st.session_state:
    st.session_state.key_index = 0
# Khởi tạo state điều khiển nếu chưa có
if "stop_ai" not in st.session_state:
    st.session_state.stop_ai = False
if "ai_thinking" not in st.session_state:
    st.session_state.ai_thinking = False
def call_gemini_retry(prompt, mode, history=[]):
    model_list = MODELS_FAST if mode == "Nhanh" else MODELS_THINKING
    gemini_history = [
        {"role": "user" if m["role"] ==
            "user" else "model", "parts": [m["content"]]}
        for m in history
    ]
    for _ in range(len(API_KEYS)):
        genai.configure(api_key=API_KEYS[st.session_state.key_index])
        for model_name in model_list:
            try:
                model = genai.GenerativeModel(model_name)
                chat = model.start_chat(history=gemini_history)
                response = chat.send_message(prompt)
                return response.text, model_name
            except:
                continue
        st.session_state.key_index = (
            st.session_state.key_index + 1) % len(API_KEYS)
    return None, None
# --- GIAO DIỆN CHÍNH ---
# --- TRONG PHẦN GIAO DIỆN CHÍNH (Sidebar) ---
with st.sidebar:
    # 1. Header - Tớ để header ở đây để giữ thương hiệu, 
    # nhưng nếu cậu muốn ẩn luôn thì đưa nó vào trong if phía dưới nhé.
    st.markdown(
        '<div class="sidebar-header"><h1>🎓</h1><h2>EduMind</h2></div>',
        unsafe_allow_html=True,
    )
    
    if not st.session_state.logged_in:
        auth_mode = st.tabs(["Đăng nhập", "Đăng ký"])
        
        with auth_mode[0]:
            user_login = st.text_input("Tên đăng nhập", key="login_user")
            pass_login = st.text_input("Mật khẩu", type="password", key="login_pass")
            # Trong phần Sidebar -> tab Đăng nhập
            if st.button("Đăng nhập", use_container_width=True):
                user_data = login_user(user_login, pass_login)
                if user_data:
                    # 1. Thiết lập trạng thái đăng nhập
                    st.session_state.logged_in = True
                    st.session_state.username = user_login
                    
                    # 2. Tải lịch sử chat RIÊNG của user này từ DB
                    user_chats = load_all_chats_from_db(user_login)
                    st.session_state.all_chats = user_chats
                    
                    # 3. Chọn cuộc trò chuyện gần nhất để hiển thị
                    if user_chats:
                        st.session_state.current_chat_id = list(user_chats.keys())[-1]
                    else:
                        st.session_state.current_chat_id = None
                        
                    st.success(f"Chào mừng {user_login} quay trở lại!")
                    time.sleep(0.5) # Đợi một chút để user thấy thông báo
                    st.rerun()
                else:
                    st.error("Sai tài khoản hoặc mật khẩu")
                    
        with auth_mode[1]:
            user_reg = st.text_input("Tên đăng nhập mới", key="reg_user")
            pass_reg = st.text_input("Mật khẩu mới", type="password", key="reg_pass")
            confirm_pass = st.text_input("Xác nhận mật khẩu", type="password")
            if st.button("Tạo tài khoản", use_container_width=True):
                if pass_reg != confirm_pass:
                    st.warning("Mật khẩu không khớp")
                elif create_user(user_reg, pass_reg):
                    st.success("Tạo tài khoản thành công! Hãy đăng nhập.")
                else:
                    st.error("Tên đăng nhập đã tồn tại")
    else:
        # Giao diện khi đã đăng nhập
        st.write(f"👤 Tài khoản: **{st.session_state.username}**")
        if st.sidebar.button("Đăng xuất"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.all_chats = {} # Xóa lịch sử hiển thị
            st.session_state.current_chat_id = None
            st.rerun()
            
    st.divider()

    # 2. Ô chọn tính năng (LUÔN HIỆN)
    choice = st.selectbox("Tính năng", ["Giải Bài Tập AI", "Tâm Lí & Sức Khoẻ", "Định Hướng Tương Lai"])

    # ---------------------------------------------------------
    # CHỈ HIỆN NẾU LÀ GIẢI BÀI TẬP AI
    # ---------------------------------------------------------
    if choice == "Giải Bài Tập AI":
        ai_mode = st.radio("Chế độ:", ["Nhanh", "Tư duy"], horizontal=True)
        st.divider()
        
        if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
            st.session_state.current_chat_id = None  # Reset về màn hình Home
            st.rerun()
            
        st.subheader("📜 Lịch sử")
        
        # Khởi tạo trạng thái đang sửa tên chat
        if "editing_chat_id" not in st.session_state:
            st.session_state.editing_chat_id = None

        # Hiển thị danh sách lịch sử (Đảo ngược để cái mới nhất lên đầu)
        for chat_id, data in list(st.session_state.all_chats.items())[::-1]:
            # Chế độ SỬA TÊN
            if st.session_state.editing_chat_id == chat_id:
                new_title = st.text_input("Sửa tên:", value=data["title"], key=f"edit_in_{chat_id}")
                col_save, col_cancel = st.columns(2)
                if col_save.button("Lưu", key=f"save_{chat_id}", use_container_width=True):
                    st.session_state.all_chats[chat_id]["title"] = new_title
                    save_chat_to_db(
                        chat_id, 
                        st.session_state.username, # Thêm cái này
                        st.session_state.all_chats[chat_id]["title"], 
                        data["messages"]
                    )
                    st.session_state.editing_chat_id = None
                    st.rerun()
                if col_cancel.button("Huỷ", key=f"cancel_{chat_id}", use_container_width=True):
                    st.session_state.editing_chat_id = None
                    st.rerun()
            
            # Chế độ HIỂN THỊ BÌNH THƯỜNG
            else:
                col_btn, col_edit, col_del = st.columns([0.65, 0.175, 0.175])
                with col_btn:
                    is_active = chat_id == st.session_state.current_chat_id
                    display_name = data["title"][:25]
                    if st.button(
                        display_name,
                        key=f"sel_{chat_id}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary",
                    ):
                        st.session_state.current_chat_id = chat_id
                        st.rerun()
                
                with col_edit:
                    if st.button("✏️", key=f"edit_btn_{chat_id}", help="Đổi tên"):
                        st.session_state.editing_chat_id = chat_id
                        st.rerun()
                
                with col_del:
                    if st.button("🗑️", key=f"del_{chat_id}", help="Xoá chat"):
                        del st.session_state.all_chats[chat_id]
                        delete_chat_from_db(chat_id)
                        if st.session_state.current_chat_id == chat_id:
                            st.session_state.current_chat_id = None
                        st.rerun()
                        
                        
# --- THÊM CSS ĐỂ ĐỔI MÀU VIỀN THANH CHAT ---
st.markdown(
    """
    
<style>
html {
        scroll-behavior: smooth;
    }
/* ===== FONT & GLOBAL ===== */
html, body, [class*="css"]  {
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    background: linear-gradient(135deg, #f5f7fa, #e4ecf7);
}
/* ===== SIDEBAR ===== */
.sidebar-header {
    text-align: center;
    margin-bottom: 20px;
}
.sidebar-header h1 {
    font-size: 40px;
    margin-bottom: 0;
}
.sidebar-header h2 {
    font-weight: 600;
    color: #4A90E2;
    letter-spacing: 1px;
}
/* ===== BUTTON CHAT LIST ===== */
div[data-testid="stVerticalBlock"] div[data-testid="stColumn"] button {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    display: block !important;
    text-align: left !important;
    border-radius: 10px !important;
    transition: all 0.25s ease;
}
/* Hover hiệu ứng gaming nhẹ */
div[data-testid="stVerticalBlock"] div[data-testid="stColumn"] button:hover {
    transform: translateX(4px);
    background: linear-gradient(90deg, #e3f2fd, #f0f7ff);
}
/* Active chat */
button[kind="primary"] {
    border: 2px solid #00c6ff !important;
    background: linear-gradient(90deg, #e0f7ff, #f5fbff) !important;
    box-shadow: 0 0 12px rgba(0,198,255,0.5);
}
/* ===== CHAT BUBBLE ===== */
[data-testid="stChatMessage"] {
    border-radius: 18px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
}
/* USER MESSAGE */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    flex-direction: row-reverse;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stChatMessageContent {
    background: linear-gradient(135deg, #4facfe, #00f2fe);
    color: black;
    border-radius: 18px 18px 0 18px;
    margin-left: 20%;
    box-shadow: 0 0 10px rgba(0,150,255,0.3);
}
div[st-target="secondary"] button {
    background-color: #ff4b4b !important;
    color: black;
    border-radius: 20px;
}
/* AI MESSAGE */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stChatMessageContent {
    background: rgba(255,255,255,0.7);
    backdrop-filter: blur(10px);
    color: #1F2937;
    border-radius: 18px 18px 18px 0;
    margin-right: 20%;
    border: 1px solid rgba(200,200,200,0.3);
}
/* ===== INPUT BOX ===== */
textarea {
    border-radius: 5px !important;
    border: 1px solid #cfd9e6 !important;
    box-shadow: 0 0 6px rgba(0,0,0,0.05);
    padding: 2px 6px;
}
/* ===== SUGGESTION BUTTON ===== */
.sug-btn button {
    background: none !important;
    border: none !important;
    color: #007BFF !important;
    padding: 4px 0 !important;
    font-style: italic !important;
    text-align: left !important;
    transition: 0.2s;
}
/* Hover glow */
.sug-btn button:hover {
    color: #00c6ff !important;
    text-shadow: 0 0 5px rgba(0,198,255,0.6);
    transform: translateX(5px);
}
/* ===== SCROLL BAR (gaming feel) ===== */
::-webkit-scrollbar {
    width: 8px;
}
::-webkit-scrollbar-thumb {
    background: linear-gradient(#4facfe, #00f2fe);
    border-radius: 10px;
}
/* ===== CARD EFFECT (glass) ===== */
[data-testid="stChatMessage"] .stChatMessageContent {
    padding: 12px 14px;
}
/* ===== ANIMATION ===== */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(5px); }
    to { opacity: 1; transform: translateY(0); }
}
[data-testid="stChatMessage"] {
    animation: fadeIn 0.3s ease;
}
</style>
""",
    unsafe_allow_html=True,
)
# --- MODULE CHÍNH ---
if choice == "Giải Bài Tập AI":
    inject_custom_ui()
    
    # Khởi tạo mặc định nếu mới vào web
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None # Mặc định là Home
        
    curr_id = st.session_state.current_chat_id

    # ---------------------------------------------------------
    # TRƯỜNG HỢP 1: MÀN HÌNH HOME (Chưa chọn/có đoạn chat nào)
    # ---------------------------------------------------------
    if curr_id is None:
        # Giao diện chào mừng giống Gemini
        st.markdown("<h2 style='text-align: center; margin-top: 10vh;'>✨ Chúng ta nên bắt đầu từ đâu nhỉ?</h2>", unsafe_allow_html=True)
        
        # Nhập câu hỏi đầu tiên
        home_input = st.chat_input("Nhập câu hỏi để bắt đầu cuộc trò chuyện mới...")
        if home_input:
            # Tạo chat mới
            new_id = str(uuid.uuid4())
            st.session_state.all_chats[new_id] = {
                "title": home_input[:25], 
                "messages": []
            }
            # Chuyển ID hiện tại sang chat mới và truyền input đi
            st.session_state.current_chat_id = new_id
            st.session_state.pending_input = home_input
            st.rerun() # Rerun để chuyển sang màn hình chat (Trường hợp 2)

    # ---------------------------------------------------------
    # TRƯỜNG HỢP 2: ĐANG TRONG 1 CUỘC TRÒ CHUYỆN
    # ---------------------------------------------------------
    else:
        # (Khởi tạo state pending_input, ai_thinking... như code cũ của bạn)
        if "pending_input" not in st.session_state:
            st.session_state.pending_input = None
        if "ai_thinking" not in st.session_state:
            st.session_state.ai_thinking = False
        if "stop_ai" not in st.session_state:
            st.session_state.stop_ai = False
            
        messages = st.session_state.all_chats[curr_id]["messages"]

        def handle_stop():
            st.session_state.stop_ai = True
            st.session_state.ai_thinking = False
            title = st.session_state.all_chats[curr_id].get("title", "Chat mới")
            save_chat_to_db(
                        chat_id, 
                        st.session_state.username, # Thêm cái này
                        st.session_state.all_chats[chat_id]["title"], 
                        data["messages"]
                    )
        

        # Hiện lịch sử
        for idx, m in enumerate(messages):
            with st.chat_message(m["role"], avatar="🐱" if m["role"] == "user" else "🎓"):
                st.markdown(m["content"])
                if m["role"] == "assistant" and "suggestions" in m:
                    for i, sug in enumerate(m["suggestions"]):
                        if st.button(f"→ {sug}", key=f"hist_{idx}_{i}"):
                            st.session_state.pending_input = sug
                            st.rerun()

        # Khu vực Input hoặc Nút Dừng
        prompt = None
        
        # Xử lý thanh chat / Nút dừng
        if st.session_state.ai_thinking:
            # Đưa nút dừng vào 1 div có class fixed-action-container để giữ nó ở đáy
            st.markdown('<div class="fixed-action-container">', unsafe_allow_html=True)
            st.button("🛑 Dừng câu trả lời", use_container_width=True, on_click=handle_stop)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            # Nếu AI không thinking, st.chat_input mặc định sẽ tự bám đáy
            user_input = st.chat_input("Nhập câu hỏi...")
            if st.session_state.pending_input:
                prompt = st.session_state.pending_input
                st.session_state.pending_input = None
            elif user_input:
                prompt = user_input

        # CHẠY AI (Giữ nguyên logic của bạn)
        if prompt:
            st.session_state.ai_thinking = True
            st.session_state.stop_ai = False
            
            # Lưu title nếu là câu hỏi đầu tiên (chưa bị đổi tên)
            if not st.session_state.all_chats[curr_id].get("title") or st.session_state.all_chats[curr_id]["title"] == "Trò chuyện mới":
                st.session_state.all_chats[curr_id]["title"] = prompt[:25]
                
            # Lưu và hiện tin nhắn của user
            messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="🐱"):
                st.markdown(prompt)
                scroll_to_bottom()
                
            with st.chat_message("assistant", avatar="🎓"):
                full_prompt = f"{prompt}\n\nSau khi trả lời xong, hãy xuống dòng và viết đúng định dạng sau: [SUG] Câu gợi ý 1 | Câu gợi ý 2 | Câu gợi ý 3."
                with st.status("EduMind đang suy nghĩ...", expanded=False) as status:
                    raw_response, _ = call_gemini_retry(
                        full_prompt, ai_mode, history=messages[:-1]
                    )
                    status.update(label="Xong!", state="complete")
                    
                if raw_response:
                    if "[SUG]" in raw_response:
                        answer_part, sug_part = raw_response.split("[SUG]")
                        current_sugs = [
                            s.strip() for s in sug_part.split("|") if s.strip()
                        ][:3]
                    else:
                        answer_part = raw_response
                        current_sugs = []
                        
                    # Tạo sẵn khung message cho assistant để cập nhật liên tục
                    assistant_msg = {
                        "role": "assistant",
                        "content": "",
                        "suggestions": [],
                    }
                    messages.append(assistant_msg)
                    placeholder = st.empty()
                    displayed_text = ""
                    
                    # Tách đoạn text chứa cả khoảng trắng/dòng mới để giữ đúng format markdown
                    tokens = re.split(r"(\s+)", answer_part.strip())
                    for token in tokens:
                        if st.session_state.get("stop_ai", False):
                            break  # Thoát ngay nếu user bấm dừng
                        displayed_text += token
                        # Cập nhật liên tục vào State.
                        messages[-1]["content"] = displayed_text
                        # Con trỏ nhấp nháy
                        placeholder.markdown(displayed_text + " ▌")
                        # Chỉ sleep ở các từ có nghĩa để tạo hiệu ứng gõ nhanh/mượt hơn
                        if token.strip():
                            time.sleep(0.015)
                            
                    # Bỏ con trỏ nhấp nháy khi hoàn thành hoặc bị dừng
                    placeholder.markdown(messages[-1]["content"])
                    
                    # Nếu AI chạy xong trọn vẹn thì mới hiển thị Suggestion
                    if not st.session_state.get("stop_ai", False):
                        messages[-1]["suggestions"] = current_sugs
                        
                    # Lưu vào Database
                    save_chat_to_db(
                        chat_id, 
                        st.session_state.username, # Thêm cái này
                        st.session_state.all_chats[chat_id]["title"], 
                        data["messages"]
                    )
                    
                    # Reset trạng thái về bình thường
                    st.session_state.ai_thinking = False
                    st.session_state.stop_ai = False
                    st.rerun()

    # Luôn đặt thẻ này ở cuối cùng để đệm khoảng trống không bị khuất bởi chat_input
    st.html("<div id='end-of-chat'></div>")



elif choice == "Tâm Lí & Sức Khoẻ":
    st.markdown("### 🌿 Trạm Sạc Năng Lượng - EduMind")
    st.caption("Nơi chia sẻ tâm tư, không lưu trữ lịch sử, hoàn toàn riêng tư.")

    # --- PHẦN 1: GỢI Ý CÂU HỎI (SUGGESTION CARDS) ---
    st.write("✨ **Cậu đang gặp vấn đề gì thế?**")
    
    # Danh sách các câu hỏi gợi ý
    suggestions = [
        "Tớ cảm thấy áp lực đồng trang lứa (Peer Pressure)...",
        "Làm sao để bớt căng thẳng trước kỳ thi sắp tới?",
        "Tớ vừa bị điểm kém, tớ thấy thất vọng về bản thân.",
        "Tớ gặp khó khăn trong việc kết bạn ở trường mới.",
        "Làm thế nào để cân bằng giữa học tập và đam mê?"
    ]

    # Hiển thị gợi ý dạng nút bấm
    cols = st.columns(2)
    selected_sug = None
    
    for i, sug in enumerate(suggestions):
        if cols[i % 2].button(sug, use_container_width=True, key=f"sug_{i}"):
            selected_sug = sug

    st.divider()

    # 2. Hiển thị Chat tạm thời
    if "temp_health_chat" not in st.session_state:
        st.session_state.temp_health_chat = []
    if "pending_health_input" not in st.session_state:
        st.session_state.pending_health_input = None

    # Vòng lặp hiển thị tin nhắn
    for idx, m in enumerate(st.session_state.temp_health_chat):
        with st.chat_message(m["role"], avatar="🌿" if m["role"] == "assistant" else "👤"):
            st.markdown(m["content"])
            # NẾU LÀ AI: Hiển thị các nút gợi ý nếu có
            if m["role"] == "assistant" and "sugs" in m:
                cols = st.columns(len(m["sugs"]))
                for i, sug in enumerate(m["sugs"]):
                    if cols[i].button(f"✨ {sug}", key=f"health_btn_{idx}_{i}", use_container_width=True):
                        st.session_state.pending_health_input = sug
                        st.rerun()

    # Xử lý Input (Thanh chat hoặc Nút gợi ý)
    h_prompt = st.chat_input("Chia sẻ tâm tư của cậu...")
    final_input = None

    if st.session_state.pending_health_input:
        final_input = st.session_state.pending_health_input
        st.session_state.pending_health_input = None
    elif h_prompt:
        final_input = h_prompt
    elif selected_sug: # Từ các thẻ gợi ý ban đầu
        final_input = selected_sug

    if final_input:
        # Lưu tin nhắn user
        st.session_state.temp_health_chat.append({"role": "user", "content": final_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(final_input)

        with st.chat_message("assistant", avatar="🌿"):
            with st.spinner("EduMind đang lắng nghe..."):
                # PROMPT MỚI: Yêu cầu AI sinh gợi ý
                sys_msg = f"""
                Bạn là chuyên gia tâm lý thấu cảm. Người dùng nói: '{final_input}'.
                Hãy trả lời câu hỏi của user, nếu câu hỏi đó chứa nỗi khó khăn user gặp phải, hãy cho họ bản chất + lời khuyên + hành động. 
                Còn user hỏi riêng thì trả lời riêng
                SAU ĐÓ, hãy đề xuất đúng 3 gợi ý để người dùng chia sẻ với AI(ví dụ như nay tôi buồn, tôi cần lời khuyên,...), lời khuyên này ngắn gọn (dưới 10 từ).
                Định dạng cuối câu trả lời: [SUG] Gợi ý 1 | Gợi ý 2 | Gợi ý 3
                """
                res, _ = call_gemini_retry(sys_msg, "Tư duy")
                
                if res:
                    # Tách phần trả lời và phần gợi ý
                    if "[SUG]" in res:
                        ans_text, sug_part = res.split("[SUG]")
                        sug_list = [s.strip() for s in sug_part.split("|")][:3]
                    else:
                        ans_text, sug_list = res, []

                    st.markdown(ans_text)
                    st.session_state.temp_health_chat.append({
                        "role": "assistant", 
                        "content": ans_text,
                        "sugs": sug_list
                    })
                    st.rerun()
                    
    # --- PHẦN 3: GÓC THƯ GIÃN (SIDEBAR HOẶC BOTTOM) ---
    with st.expander("🧘 Một vài kỹ thuật thư giãn nhanh"):
        st.markdown("""
        - **Quy tắc 5-4-3-2-1:** Tìm 5 thứ bạn thấy, 4 thứ bạn chạm, 3 thứ bạn nghe, 2 thứ bạn ngửi, 1 thứ bạn nếm.
        - **Hít thở sâu:** Hít vào 4 giây, giữ 4 giây, thở ra 8 giây.
        """)
        
        

# MODULE: ĐỊNH HƯỚNG TƯƠNG LAI
elif choice == "Định Hướng Tương Lai":
    st.markdown("<h2 style='text-align: center;'>🧭 La Bàn Định Hướng</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Khám phá tiềm năng, xây lộ trình và thử nghiệm nghề nghiệp thực tế.</p>", unsafe_allow_html=True)
    st.divider()

    # Tạo 3 tab chức năng chuẩn quốc tế
    tab1, tab2, tab3 = st.tabs(["🧩 Khám Phá Ikigai", "🗺️ Lộ Trình Ngược (Reverse Roadmap)", "💼 Giả Lập Nghề Nghiệp (Simulation)"])

    # ==========================================
    # TAB 1: MA TRẬN IKIGAI (Phân tích điểm chạm)
    # ==========================================
    with tab1:
        st.subheader("1. Khám phá vùng giao thoa nghề nghiệp")
        st.info("Nhập các từ khóa ngắn gọn. Trí tuệ nhân tạo sẽ tìm ra 'điểm chạm' giữa đam mê của cậu và nhu cầu thị trường.")
        


        
        col1, col2 = st.columns(2)
        with col1:
            passion = st.text_area("🌟 Đam mê & Sở thích:", placeholder="Ví dụ: Thích giải thuật toán C++, phân tích biểu đồ nến, tổ chức giải cầu lông...")
            strength = st.text_area("💪 Kỹ năng thế mạnh:", placeholder="Ví dụ: Tư duy logic (HLD, DP), code Python/C++, giao tiếp tiếng Trung...")
        with col2:
            market = st.text_area("📈 Xu hướng thị trường cậu quan tâm:", placeholder="Ví dụ: AI, Quantitative Trading, Công nghệ giáo dục (EdTech)...")
            salary = st.text_input("💰 Mức thu nhập kỳ vọng (/tháng):", placeholder="Ví dụ: 30k - 50k (Không cần ghi đơn vị tiền tệ)")

        if st.button("🔍 Phân tích Ma trận Ikigai", type="secondary", use_container_width=True):
            if passion and strength:
                with st.spinner("Đang tổng hợp dữ liệu và tìm kiếm cơ hội..."):
                    sys_msg = f"""
                    Phân tích Ikigai cho người dùng với dữ liệu: 
                    Đam mê: {passion}, Điểm mạnh: {strength}, Thị trường: {market}, Kỳ vọng lương: {salary}.
                    Hãy đề xuất 3 nghề nghiệp cụ thể, ngách thị trường tiềm năng phù hợp nhất. 
                    Mỗi nghề nghiệp nêu rõ: 
                    - Tên vị trí (Tiếng Việt & Tiếng Anh).
                    - Lý do phù hợp với dữ liệu trên.
                    - Các kỹ năng cần bổ sung ngay lập tức.
                    Sử dụng định dạng Markdown, rõ ràng, hiện đại. Nếu có nhắc đến tiền, định dạng số với chữ 'k' (VD: 50k, 100k) và tuyệt đối không dùng ký hiệu đô la.
                    """
                    res, _ = call_gemini_retry(sys_msg, "Tư duy")
                    if res:
                        st.success("Tạo phân tích thành công!")
                        st.markdown(res)
            else:
                st.warning("Cậu điền ít nhất Đam mê và Điểm mạnh để AI phân tích nhé!")

    # ==========================================
    # TAB 2: LỘ TRÌNH NGƯỢC (REVERSE ENGINEERING)
    # ==========================================
    with tab2:
        st.subheader("2. Thiết kế Lộ Trình Ngược")
        st.write("Xác định mục tiêu cuối cùng, hệ thống sẽ chẻ nhỏ thành các cột mốc lùi dần về hiện tại.")
        
        goal = st.text_input("🎯 Mục tiêu lớn nhất của cậu (1-5 năm tới):", placeholder="Ví dụ: Đạt HSK 6 để nhận học bổng du học Trung Quốc năm 2027, hoặc trở thành Quant Developer.")
        timeframe = st.slider("Thời gian hoàn thành (Năm):", 1, 10, 3)
        
        if st.button("🚀 Xây dựng Timeline", use_container_width=True):
            if goal:
                with st.spinner(f"Đang tính toán các cột mốc lùi từ năm {2026 + timeframe} về 2026..."):
                    sys_msg = f"""
                    Áp dụng phương pháp Reverse Engineering (Kỹ thuật dịch ngược) để lên lộ trình {timeframe} năm cho mục tiêu: "{goal}".
                    Bắt đầu từ kết quả cuối cùng ở năm {2026 + timeframe}, lùi dần từng năm về hiện tại (Năm nay là 2026, người dùng học lớp 11).
                    Với mỗi giai đoạn, chỉ ra: 
                    - Cột mốc cần đạt (Milestone).
                    - Hành động cụ thể cần làm (Actionable steps).
                    - Rủi ro có thể gặp phải và cách phòng tránh.
                    Trình bày bằng Markdown, sử dụng bullet points rõ ràng.
                    """
                    res, _ = call_gemini_retry(sys_msg, "Tư duy")
                    if res:
                        st.markdown(res)
                        
                        # Thêm nút tải file (Tùy chọn nâng cao)
                        st.download_button(
                            label="📥 Tải Lộ Trình (TXT)",
                            data=res,
                            file_name="Lo_Trinh_Tuong_Lai.txt",
                            mime="text/plain"
                        )
            else:
                st.warning("Nhập mục tiêu để bắt đầu nào!")

    # ==========================================
    # TAB 3: GIẢ LẬP NGHỀ NGHIỆP (SIMULATION)
    # ==========================================
    with tab3:
        st.subheader("3. Trải nghiệm Tình huống Thực tế")
        st.write("Thử đóng vai vào một vị trí công việc xem cậu có thực sự chịu được áp lực của nó không.")
        
        roles = [
            "Software Engineer (Kỹ sư phần mềm)", 
            "Quantitative Researcher (Nghiên cứu định lượng)", 
            "Data Analyst (Chuyên viên phân tích dữ liệu)", 
            "Project Manager (Quản lý dự án EduTech)"
        ]
        selected_role = st.selectbox("Chọn vai trò cậu muốn thử nghiệm:", roles)
        
        if "sim_active" not in st.session_state:
            st.session_state.sim_active = False
            
        if st.button("🎭 Bắt đầu ngày làm việc", type="secondary"):
            st.session_state.sim_active = True
            with st.spinner("Đang khởi tạo tình huống..."):
                sys_msg = f"""
                Tạo một tình huống thực tế KHÓ KHĂN mà một {selected_role} thường gặp phải trong công việc hàng ngày.
                Tình huống cần gay cấn (ví dụ: thị trường sập mạnh, thuật toán chạy quá chậm O(N^2) cần tối ưu, hoặc mâu thuẫn team).
                Kết thúc bằng câu hỏi: "Với tư cách là {selected_role}, bạn sẽ xử lý tình huống này thế nào?".
                """
                res, _ = call_gemini_retry(sys_msg, "TƯ duy")
                st.session_state.sim_context = res
                st.session_state.sim_history = [{"role": "assistant", "content": res}]

        # Hiển thị khu vực tương tác nếu Simulation đang chạy
        if st.session_state.get("sim_active", False):
            st.divider()
            for m in st.session_state.sim_history:
                with st.chat_message(m["role"], avatar="💼" if m["role"] == "assistant" else "👤"):
                    st.markdown(m["content"])
            
            sim_ans = st.chat_input("Nhập cách giải quyết của cậu...")
            if sim_ans:
                st.session_state.sim_history.append({"role": "user", "content": sim_ans})
                with st.chat_message("user", avatar="👤"):
                    st.markdown(sim_ans)
                
                with st.chat_message("assistant", avatar="💼"):
                    with st.spinner("Sếp đang đánh giá cách xử lý của cậu..."):
                        eval_msg = f"""
                        Tình huống: {st.session_state.sim_context}
                        Cách giải quyết của ứng viên: {sim_ans}
                        Hãy đánh giá cách xử lý này như một người quản lý cấp cao.
                        Chỉ ra điểm tốt, điểm rủi ro và gợi ý cách xử lý tối ưu hơn ở môi trường doanh nghiệp.
                        """
                        res, _ = call_gemini_retry(eval_msg, "Tư duy")
                        st.markdown(res)
                        st.session_state.sim_history.append({"role": "assistant", "content": res})
                
                if st.button("⏹️ Kết thúc phiên mô phỏng"):
                    st.session_state.sim_active = False
                    st.session_state.sim_history = []
                    st.rerun()
                    
                    



# Đặt dòng này ở cuối file app.py của bạn
st.markdown("<div id='end-of-chat'></div>", unsafe_allow_html=True)
