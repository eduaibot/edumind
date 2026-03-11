import streamlit as st
import google.generativeai as genai

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="EduMind AI", page_icon="🎓", layout="wide")

# --- KẾT NỐI API (Bảo mật qua Secrets) ---
# Khi chạy online, bạn sẽ dán API Key vào phần Settings của Streamlit Cloud
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Chưa tìm thấy API Key! Hãy cấu hình trong phần Secrets.")

# --- SIDEBAR - THANH ĐIỀU HƯỚNG ---
with st.sidebar:
    st.title("🛡️ EduMind Hub")
    st.info("Trợ lý toàn diện cho học sinh Gen Z")
    choice = st.option_menu(
        menu_title="Tính năng chính",
        options=["Tâm Lý & Sức Khỏe", "Giải Bài Tập AI", "Định Hướng Tương Lai"],
        icons=["heart", "book", "compass"],
        default_index=0,
    )

# --- MODULE 1: TÂM LÝ & SỨC KHỎE ---
if choice == "Tâm Lý & Sức Khỏe":
    st.header("💬 Trạm Sẻ Chia Tâm Hồn")
    st.write("Đừng giữ nỗi buồn một mình, hãy tâm sự với mình nhé!")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Hôm nay bạn thấy thế nào?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # System Prompt để AI đóng vai chuyên gia tâm lý
            system_prompt = "Bạn là chuyên gia tư vấn tâm lý học đường hiền hậu. Hãy lắng nghe và an ủi học sinh sau đây: "
            response = model.generate_content(system_prompt + prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

# --- MODULE 2: GIẢI BÀI TẬP AI ---
elif choice == "Giải Bài Tập AI":
    st.header("📚 Gia Sư Thông Thái")
    st.write("Tải ảnh đề bài hoặc nhập câu hỏi khó tại đây.")
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("Gửi ảnh đề bài (Toán, Lý, Hóa, Anh...)", type=["jpg", "png", "jpeg"])
    with col2:
        user_question = st.text_area("Hoặc dán nội dung câu hỏi vào đây:")

    if st.button("Giải đáp ngay"):
        if uploaded_file or user_question:
            with st.spinner("Đang suy nghĩ..."):
                # Logic gọi AI xử lý đa phương thức (ảnh + chữ)
                content = ["Hãy giải chi tiết bài tập này và giải thích các bước:", uploaded_file if uploaded_file else user_question]
                response = model.generate_content(content)
                st.success("Kết quả gợi ý:")
                st.write(response.text)
        else:
            st.warning("Vui lòng nhập câu hỏi hoặc tải ảnh lên!")

# --- MODULE 3: ĐỊNH HƯỚNG TƯƠNG LAI ---
elif choice == "Định Hướng Tương Lai":
    st.header("🧭 La Bàn Nghề Nghiệp")
    st.subheader("Trắc nghiệm nhanh sở thích")
    
    hobby = st.multiselect("Bạn thích làm gì nhất?", ["Lập trình", "Vẽ/Thiết kế", "Kinh doanh", "Viết lách", "Chăm sóc cây cối"])
    if st.button("Xem gợi ý nghề nghiệp"):
        if hobby:
            res = model.generate_content(f"Dựa trên sở thích {hobby}, hãy gợi ý 3 ngành nghề hot nhất năm 2026 và lộ trình học.")
            st.balloons()
            st.write(res.text)