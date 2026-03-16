from PIL import Image
import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load biến môi trường từ .env (nếu có)
load_dotenv()

st.set_page_config(page_title="EduMind AI", page_icon="🎓", layout="wide")

# --- QUẢN LÝ API KEY ---
def get_api_key():
    # Thử lấy từ st.secrets trước (ưu tiên trên web)
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except:
        pass
    # Nếu không có (khi chạy local) thì mới lấy từ env
    return os.getenv("GEMINI_API_KEY")

key = get_api_key()

if key:
    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name="models/gemini-3.1-flash-lite-preview")
    # Đoạn code này sẽ liệt kê các model bạn có quyền dùng
else:
    st.error("Cảnh báo: Thiếu GEMINI_API_KEY. Hãy kiểm tra lại file .env hoặc Secrets.")
    st.stop()

import io

# --- HÀM TỐI ƯU HÓA ẢNH (GIÚP LOAD DƯỚI 1S) ---
def optimize_image(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # Resize để AI vẫn đọc tốt nhưng file nhẹ hơn
    max_size = 1024
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    
    # Nén JPEG để tốc độ truyền tải nhanh nhất
    tmp_file = io.BytesIO()
    img.save(tmp_file, format="JPEG", quality=75)
    tmp_file.seek(0)
    return Image.open(tmp_file)

# --- KHU VỰC HIỂN THỊ ẢNH (Dùng Fragment để load thần tốc) ---
@st.fragment
def image_processing_unit():
    # Cột cho nút thêm và khung xem trước
    col_add, col_status = st.columns([1, 3])
    
    with col_add:
        with st.popover("📷 Thêm hình ảnh", width='stretch'):
            new_imgs = st.file_uploader(
                "Chọn ảnh đề bài", 
                type=["jpg", "png", "jpeg"], 
                accept_multiple_files=True, 
                label_visibility="collapsed"
            )
            if new_imgs:
                for img in new_imgs:
                    # Nén ngay khi upload
                    opt_img = optimize_image(img)
                    if opt_img not in st.session_state.pending_images:
                        st.session_state.pending_images.append(opt_img)
                st.rerun(scope="fragment")

    if st.session_state.pending_images:
        st.write("🖼️ Danh sách ảnh chờ gửi:")
        img_cols = st.columns(5)
        for i, img_obj in enumerate(st.session_state.pending_images):
            with img_cols[i % 5]:
                st.image(img_obj, width='stretch')
                if st.button(f"✖", key=f"del_{i}"):
                    st.session_state.pending_images.pop(i)
                    st.rerun(scope="fragment")


# --- GIAO DIỆN ---
with st.sidebar:
    st.title("🛡️ EduMind Hub")
    choice = st.selectbox(
        "Tính năng chính",
        ["Giải Bài Tập AI", "Tâm Lý & Sức Khỏe", "Định Hướng Tương Lai"]
    )

if choice == "Tâm Lý & Sức Khỏe":
    st.header("💬 Trạm Sẻ Chia Tâm Hồn")
    
    # --- TÍNH NĂNG 1: ĐO CẢM XÚC NHANH ---
    st.subheader("Hôm nay tâm trạng của bạn màu gì?")
    col_mood, col_desc = st.columns([1, 3])
    with col_mood:
        mood_color = st.color_picker("Chọn một màu đại diện cho bạn lúc này", "#00f900")
    with col_desc:
        st.write("Mỗi màu sắc đều nói lên một điều gì đó. Hãy để mình lắng nghe bạn nhé.")

    # --- TÍNH NĂNG 2: NÚT BÁO ĐỘNG ĐỎ (EXPANDER) ---
    with st.expander("🚨 CẦN TRỢ GIÚP KHẨN CẤP?"):
        st.error("Nếu bạn đang cảm thấy quá bế tắc, hãy nhớ luôn có người sẵn sàng bên bạn:")
        st.markdown("- **Tổng đài Quốc gia Bảo vệ Trẻ em:** 111")
        st.markdown("- **Đường dây nóng hỗ trợ tâm lý:** 1900xxxx")

    st.divider()

    # --- TÍNH NĂNG 3: CHATBOT CHỮA LÀNH ---
    # Thiết lập System Instruction chi tiết hơn
    SYSTEM_INSTRUCTION = f"""
    Bạn là một chuyên gia tâm lý học đường tên là 'EduMind'. 
    Người dùng đang cảm thấy có tâm trạng tương ứng với mã màu {mood_color}.
    - Nếu màu tối/lạnh: Hãy an ủi nhẹ nhàng.
    - Nếu màu sáng/ấm: Hãy cùng chia sẻ niềm vui.
    Luôn dùng ngôn từ gen Z thân thiện (cậu - tớ, mình - bạn). 
    Tuyệt đối không đưa ra lời khuyên y khoa, chỉ mang tính chất tham vấn tâm lý học đường.
    """

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Hiển thị lịch sử chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Ô nhập liệu chat
    if prompt := st.chat_input("Bạn đang nghĩ gì thế?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            full_prompt = f"{SYSTEM_INSTRUCTION}\nTin nhắn của học sinh: {prompt}"
            response = model.generate_content(full_prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

    # --- TÍNH NĂNG 4: NHẬT KÝ BIẾT ƠN (SIDEBAR HOẶC BOTTOM) ---
    st.divider()
    with st.container():
        st.subheader("📝 Góc Biết Ơn")
        gratitude = st.text_input("Viết 1 điều nhỏ bé khiến bạn mỉm cười hôm nay:")
        if st.button("Lưu vào tim"):
            if gratitude:
                st.toast(f"Đã lưu: '{gratitude}' vào bộ nhớ hạnh phúc!", icon='💖')
                st.balloons()

elif choice == "Giải Bài Tập AI":
    st.header("📚 Gia Sư Thông Thái 4.0")

    # Khởi tạo session state
    if "pending_images" not in st.session_state:
        st.session_state.pending_images = []
    if "study_messages" not in st.session_state:
        st.session_state.study_messages = []

    # 1. Hiển thị lịch sử Chat
    chat_container = st.container()
    with chat_container:
        for m in st.session_state.study_messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if "images" in m and m["images"]:
                    cols_hist = st.columns(min(len(m["images"]), 4))
                    for idx, img in enumerate(m["images"]):
                        cols_hist[idx % 4].image(img, width='stretch')

    st.write("---")
    
    # 2. Gọi khu vực xử lý ảnh (Fragment giúp mượt mà)
    image_processing_unit()

    # 3. Khung Chat Input
    if user_question := st.chat_input("Nhập câu hỏi hoặc yêu cầu giải bài tại đây..."):
        # Lấy ảnh đang chờ
        current_imgs = list(st.session_state.pending_images)
        
        # Lưu vào lịch sử phía người dùng
        st.session_state.study_messages.append({
            "role": "user", 
            "content": user_question,
            "images": current_imgs
        })

        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_question)
                if current_imgs:
                    cols_pre = st.columns(min(len(current_imgs), 4))
                    for i, img in enumerate(current_imgs):
                        cols_pre[i % 4].image(img, width='stretch')

            with st.chat_message("assistant"):
                with st.spinner("Gia sư đang phân tích đề bài..."):
                    # Gửi tới Gemini (Cần đảm bảo biến 'model' đã được định nghĩa ở đầu app)
                    prompt = "Bạn là gia sư chuyên nghiệp. Hãy giải thích chi tiết, trình bày khoa học bằng Markdown và Latex nếu có công thức."
                    content_to_send = [prompt + "\n" + user_question] + current_imgs
                    
                    try:
                        response = model.generate_content(content_to_send)
                        st.markdown(response.text)
                        st.session_state.study_messages.append({
                            "role": "assistant", 
                            "content": response.text
                        })
                    except Exception as e:
                        st.error(f"Lỗi kết nối AI: {e}")
        
        # Xóa sạch ảnh chờ và rerun để reset giao diện
        st.session_state.pending_images = []
        st.rerun()

elif choice == "Định Hướng Tương Lai":
    st.header("🧭 La Bàn Nghề Nghiệp")
    h = st.multiselect("Sở thích:", ["Lập trình", "Vẽ", "Kinh doanh", "Viết lách", "Khác"])
    if st.button("Gợi ý"):
        if h:
            res = model.generate_content(f"Dựa trên sở thích {h}, gợi ý 3 nghề nghiệp hot 2026.")
            st.balloons()
            st.write(res.text)

# In ra danh sách model khả dụng vào Log để xem
for m in genai.list_models():
    print(m.name)