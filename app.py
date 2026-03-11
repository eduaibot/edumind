import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load biến môi trường từ .env (nếu có)
load_dotenv()

st.set_page_config(page_title="EduMind AI", page_icon="🎓", layout="wide")

# --- QUẢN LÝ API KEY ---
def get_api_key():
    # 1. Thử lấy từ môi trường (local .env hoặc system env)
    key = os.getenv("GEMINI_API_KEY")
    # 2. Nếu không thấy, thử lấy từ st.secrets (Streamlit Cloud)
    if not key and "GEMINI_API_KEY" in st.secrets:
        key = st.secrets["GEMINI_API_KEY"]
    return key

key = get_api_key()

if key:
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    # Đoạn code này sẽ liệt kê các model bạn có quyền dùng
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
else:
    st.error("Cảnh báo: Thiếu GEMINI_API_KEY. Hãy kiểm tra lại file .env hoặc Secrets.")
    st.stop()

# --- GIAO DIỆN ---
with st.sidebar:
    st.title("🛡️ EduMind Hub")
    choice = st.selectbox(
        "Tính năng chính",
        ["Tâm Lý & Sức Khỏe", "Giải Bài Tập AI", "Định Hướng Tương Lai"]
    )

if choice == "Tâm Lý & Sức Khỏe":
    st.header("💬 Trạm Sẻ Chia Tâm Hồn")
    if "msgs" not in st.session_state:
        st.session_state.msgs = []

    for m in st.session_state.msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if p := st.chat_input("Hôm nay bạn thấy thế nào?"):
        st.session_state.msgs.append({"role": "user", "content": p})
        with st.chat_message("user"):
            st.markdown(p)

        with st.chat_message("assistant"):
            sys_p = "Bạn là chuyên gia tư vấn tâm lý học đường hiền hậu. Hãy lắng nghe và an ủi: "
            resp = model.generate_content(sys_p + p)
            st.markdown(resp.text)
            st.session_state.msgs.append({"role": "assistant", "content": resp.text})

elif choice == "Giải Bài Tập AI":
    st.header("📚 Gia Sư Thông Thái")
    c1, c2 = st.columns(2)
    with c1:
        f = st.file_uploader("Gửi ảnh đề bài", type=["jpg", "png", "jpeg"])
    with c2:
        q = st.text_area("Hoặc dán câu hỏi:")

    if st.button("Giải đáp"):
        if f or q:
            with st.spinner("Đang giải..."):
                cnt = ["Giải chi tiết và giải thích các bước:", f if f else q]
                resp = model.generate_content(cnt)
                st.success("Kết quả:")
                st.write(resp.text)

elif choice == "Định Hướng Tương Lai":
    st.header("🧭 La Bàn Nghề Nghiệp")
    h = st.multiselect("Sở thích:", ["Lập trình", "Vẽ", "Kinh doanh", "Viết lách", "Khác"])
    if st.button("Gợi ý"):
        if h:
            res = model.generate_content(f"Dựa trên sở thích {h}, gợi ý 3 nghề nghiệp hot 2026.")
            st.balloons()
            st.write(res.text)