import streamlit as st
import random
import json
import os
import streamlit.components.v1 as components
from datetime import datetime
import pandas as pd

# --- CẤU HÌNH HỆ THỐNG & FILE ---
DATA_DIR = "user_data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
DB_FILE = os.path.join(DATA_DIR, "notebooks.json")
SESSION_FILE = os.path.join(DATA_DIR, "session.json")

if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

# --- 15 THEMES MODERN TECH ---
THEMES = {
    "Ocean Blue (G)": {"bg": "#f0f9ff", "main": "#0ea5e9", "text": "#0c4a6e", "border": "#bae6fd", "grad": "linear-gradient(135deg, #e0f2fe 0%, #7dd3fc 100%)", "neon": "0 0 10px #0ea5e9"},
    "Sakura Pink (G)": {"bg": "#fff0f6", "main": "#f55eb1ff", "text": "#831843", "border": "#fbcfe8", "grad": "linear-gradient(135deg, #fce7f3 0%, #f9a8d4 100%)", "neon": "0 0 10px #ec4899"},
    "Cyberpunk (G)": {"bg": "#0f172a", "main": "#fde047", "text": "#e2e8f0", "border": "#334155", "grad": "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)", "neon": "0 0 15px #fde047"},
    "Neon Matrix (G)": {"bg": "#020617", "main": "#22c55e", "text": "#f8fafc", "border": "#064e3b", "grad": "linear-gradient(135deg, #065f46 0%, #022c22 100%)", "neon": "0 0 15px #22c55e"},
    "Sunset Glow (G)": {"bg": "#fff7ed", "main": "#f97316", "text": "#7c2d12", "border": "#fed7aa", "grad": "linear-gradient(135deg, #ffedd5 0%, #fdba74 100%)", "neon": "0 0 10px #f97316"},
    "Deep Forest (G)": {"bg": "#f0fdf4", "main": "#20be5a", "text": "#14532d", "border": "#bbf7d0", "grad": "linear-gradient(135deg, #dcfce7 0%, #86efac 100%)", "neon": "0 0 10px #16a34a"},
    "Royal Purple (G)": {"bg": "#faf5ff", "main": "#a855f7", "text": "#581c87", "border": "#e9d5ff", "grad": "linear-gradient(135deg, #f3e8ff 0%, #d8b4fe 100%)", "neon": "0 0 10px #a855f7"},
    "Midnight (G)": {"bg": "#f8fafc", "main": "#334155", "text": "#0f172a", "border": "#e2e8f0", "grad": "linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%)", "neon": "0 0 10px #334155"},
    "Blood Moon (G)": {"bg": "#1a0505", "main": "#dc2626", "text": "#fee2e2", "border": "#7f1d1d", "grad": "linear-gradient(135deg, #450a0a 0%, #220505 100%)", "neon": "0 0 15px #dc2626"},
    "Glacier (G)": {"bg": "#f8fafc", "main": "#06b6d4", "text": "#164e63", "border": "#a5f3fc", "grad": "linear-gradient(135deg, #cffafe 0%, #67e8f9 100%)", "neon": "0 0 10px #06b6d4"},
    "Amethyst (G)": {"bg": "#170f1e", "main": "#c084fc", "text": "#f3e8ff", "border": "#581c87", "grad": "linear-gradient(135deg, #3b0764 0%, #170f1e 100%)", "neon": "0 0 15px #c084fc"},
    "Lava (G)": {"bg": "#2a0800", "main": "#ef4444", "text": "#ffedd5", "border": "#9a3412", "grad": "linear-gradient(135deg, #7c2d12 0%, #431407 100%)", "neon": "0 0 15px #ef4444"},
    "Obsidian (G)": {"bg": "#09090b", "main": "#71717a", "text": "#fafafa", "border": "#27272a", "grad": "linear-gradient(135deg, #18181b 0%, #09090b 100%)", "neon": "0 0 10px #71717a"},
    "Gold Leaf (G)": {"bg": "#fffbeb", "main": "#eab308", "text": "#713f12", "border": "#fde047", "grad": "linear-gradient(135deg, #fef3c7 0%, #fde047 100%)", "neon": "0 0 10px #eab308"},
    "Toxic (G)": {"bg": "#051f0e", "main": "#84cc16", "text": "#ecfccb", "border": "#3f6212", "grad": "linear-gradient(135deg, #1a2e05 0%, #051f0e 100%)", "neon": "0 0 15px #84cc16"}
}

# --- TIỆN ÍCH DỮ LIỆU ---
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def parse_data(raw_text):
    words = []
    for line in raw_text.strip().split('\n'):
        if not line.strip(): continue
        parts = [p.strip() for p in line.split('-')]
        # Bỏ STT nếu có
        if parts and parts[0].isdigit(): parts = parts[1:]
        
        # Cấu trúc: [0]Hz - [1]Py - [2]Vn - [3]ExHz - [4]ExPy - [5]ExVn
        if len(parts) >= 6:
            words.append({
                'hz': parts[0], 'py': parts[1], 'vn': parts[2],
                'ex_hz': parts[3], 'ex_py': parts[4], 'ex_vn': parts[5]
            })
        elif len(parts) >= 3: # Hỗ trợ dữ liệu cũ không có ví dụ
            words.append({
                'hz': parts[0], 'py': parts[1], 'vn': " - ".join(parts[2:]),
                'ex_hz': '', 'ex_py': '', 'ex_vn': ''
            })
    return words

def get_step_options(n):
    # Tạo danh sách các lựa chọn kích thước Set: 5, 10, 15... đến n/2
    # Dùng set() để tránh trùng lặp và sorted() để sắp xếp tăng dần
    options = [i for i in range(5, (n // 2) + 1, 5)]
    
    # Luôn thêm chính n vào để có tùy chọn "Học tất cả"
    options.append(n)
    
    # Loại bỏ trùng lặp (ví dụ n=10 thì n/2 là 5, đã có trong list)
    unique_options = sorted(list(set(options)))
    
    # Đảm bảo slider có ít nhất 2 giá trị để không bị lỗi RangeError
    if len(unique_options) < 2:
        return [5, n] if n > 5 else [1, n]
        
    return unique_options

def format_to_text_6_cols(words_list):
    lines = []
    for i, w in enumerate(words_list, 1):
        # Thêm STT vào đầu dòng: "1 - Hán - Py - Nghĩa - VD Hán - VD Py - VD Nghĩa"
        line = f"{i} - {w['hz']} - {w['py']} - {w['vn']} - {w.get('ex_hz','')} - {w.get('ex_py','')} - {w.get('ex_vn','')}"
        # Xóa các khoảng trắng và dấu gạch dư thừa ở cuối dòng
        lines.append(line.strip(" -"))
    return "\n".join(lines)

# --- QUẢN LÝ SESSION & TRẠNG THÁI ---
if 'users' not in st.session_state: st.session_state.users = load_json(USERS_FILE, {})
if 'notebooks' not in st.session_state: st.session_state.notebooks = load_json(DB_FILE, {})
if 'session' not in st.session_state: st.session_state.session = load_json(SESSION_FILE, {"remembered": None})

# Auto-login
if 'current_user' not in st.session_state:
    st.session_state.current_user = st.session_state.session.get("remembered")

# --- AUTHENTICATION MODULE ---
if not st.session_state.current_user:
    st.title("🔒 HSK System Login")
    auth_mode = st.radio("Chế độ:", ["Đăng nhập", "Đăng ký"], horizontal=True)
    username = st.text_input("Username").strip().lower()
    password = st.text_input("Password", type="password")
    remember = st.checkbox("Ghi nhớ đăng nhập")
    
    if st.button("Xác nhận"):
        if auth_mode == "Đăng ký":
            if username in st.session_state.users:
                st.error("Tài khoản đã tồn tại!")
            elif username and password:
                is_admin = (username == "akaide")
                st.session_state.users[username] = {"password": password, "is_admin": is_admin, "theme": "Ocean Blue (G)"}
                save_json(USERS_FILE, st.session_state.users)
                st.success("Đăng ký thành công! Hãy đăng nhập.")
        else:
            if username in st.session_state.users and st.session_state.users[username]["password"] == password:
                st.session_state.current_user = username
                if remember:
                    st.session_state.session["remembered"] = username
                    save_json(SESSION_FILE, st.session_state.session)
                st.rerun()
            else:
                st.error("Sai tài khoản hoặc mật khẩu!")
    st.stop()

# --- LOAD USER PROGRESS ---
user = st.session_state.current_user
user_info = st.session_state.users[user]
is_admin = user_info.get("is_admin", False)
PROG_FILE = os.path.join(DATA_DIR, f"progress_{user}.json")

if 'progress' not in st.session_state: 
    st.session_state.progress = load_json(PROG_FILE, {"history": [], "words": {}, "resume_state": None})

if 'theme_name' not in st.session_state: 
    st.session_state.theme_name = user_info.get("theme", "Ocean Blue (G)")

# Phục hồi State (Resume)
if st.session_state.progress["resume_state"] and 'mode' not in st.session_state:
    for k, v in st.session_state.progress["resume_state"].items():
        st.session_state[k] = v
elif 'mode' not in st.session_state:
    st.session_state.mode = "manage"

def sync_progress():
    save_json(PROG_FILE, st.session_state.progress)

def save_resume_state():
    if st.session_state.mode == "study":
        st.session_state.progress["resume_state"] = {
            "mode": "study", "qs": st.session_state.qs, "curr_nb": st.session_state.curr_nb, 
            "idx": st.session_state.idx, "answered": st.session_state.answered, "is_correct": st.session_state.get('is_correct', False)
        }
    else:
        st.session_state.progress["resume_state"] = None
    sync_progress()

# --- CSS TECH UI ---
t = THEMES[st.session_state.theme_name]
st.set_page_config(
    page_title="HSK Smart 2.0", 
    page_icon="logo.png",
    layout="wide"
)

st.markdown("""
    <style>
        /* Ẩn nút 'Manage app' và các hiệu ứng liên quan ở góc dưới */
        #stDecoration {display:none;}
        [data-testid="stStatusWidget"] {display:none;}
        
        /* Chặn hoàn toàn nút Deploy/Manage app nếu nó xuất hiện ở góc dưới phải hoặc trái */
        .stAppDeployButton {display:none;}
        
        /* Tối ưu không gian nội dung */
        .block-container {
            margin-top: 2rem;
            padding-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <style>
    .stApp {{ background-color: {t['bg']}; color: {t['text']}; font-family: 'Inter', sans-serif; transition: 0.3s; }}
    /* Glassmorphism */
    div[data-testid="stExpander"], .stAlert, div[data-testid="stForm"], .glass-box {{
        background: rgba(255, 255, 255, 0.4) !important;
        backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
        border: 1px solid {t['border']} !important;
        border-radius: 15px !important; padding: 15px !important; margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }}
    .question-container {{ 
        background: {t['grad']} !important; border-left: 8px solid {t['main']} !important; 
        text-align: center; border-radius: 20px; padding: 30px; margin-bottom: 15px;
        box-shadow: {t['neon']}; transition: 0.3s;
    }}
    .stButton > button {{ 
        background-color: {t['main']} !important; color: white !important; 
        border-radius: 8px !important; border: none; font-weight: bold; transition: 0.3s;
    }}
    .stButton > button:hover {{ box-shadow: {t['neon']}; opacity: 0.9; }}
    .stTextInput input {{ text-align: center; border-radius: 10px !important; font-size: 20px;}}
    
    /* Responsive Table */
    .dataframe {{ width: 100% !important; }}
    /* Thu nhỏ padding của container chính để tiết kiệm chỗ */
    .block-container {{ padding-top: 1rem !important; padding-bottom: 0rem !important; }}
    
    /* Container đáp án chia đôi */
    .answer-card {{
        display: flex;
        flex-direction: row;
        gap: 10px;
        align-items: center;
        padding: 10px !important;
        margin-top: 5px !important;
    }}
    .ans-left {{ 
        flex: 1; border-right: 1px solid {t['border']}; 
        text-align: center; padding-right: 5px;
    }}
    .ans-right {{ flex: 1.5; font-size: 0.85rem; line-height: 1.3; }}
    
    /* Tối ưu nút Thoát và Tiêu đề trên 1 dòng */
    .header-container {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        flex-wrap: nowrap; /* Ép trên 1 dòng */
    }}
    .header-title {{ 
        font-size: 1rem; font-weight: bold; white-space: nowrap; 
        overflow: hidden; text-overflow: ellipsis; margin-right: 10px;
    }}
    
    /* Nút kiểm tra nhỏ gọn */
    .stButton > button[key*="check"] {{
        padding: 0.2rem 0.5rem !important;
        font-size: 0.8rem !important;
    }}
    </style>
    
    """, unsafe_allow_html=True)

# --- AUTO FOCUS JS TRICK ---
def auto_focus():
    components.html("""
        <script>
        const inputs = parent.document.querySelectorAll('input[type="text"]');
        if (inputs.length > 0) { inputs[inputs.length - 1].focus(); }
        </script>
    """, height=0)

# --- UI QUẢN LÝ ---
import random
from datetime import datetime
import pandas as pd
import streamlit as st

if st.session_state.mode == "manage":
    
    # --- 0. MIGRATION & ĐỒNG BỘ HÓA (FIX TRIỆT ĐỂ BẰNG HÁN TỰ) ---
    def migrate_to_hz_order():
        updated = False
        for name, info in st.session_state.notebooks.items():
            current_words = info.get('words', [])
            
            # Dọn dẹp dữ liệu rác từ các phiên bản cũ
            if 'fixed_word_order' in info:
                info['fixed_hz_order'] = [w.get('hz') for w in info['fixed_word_order'] if w.get('hz')]
                del info['fixed_word_order']
                updated = True
                
            if 'fixed_order_indices' in info:
                hz_order = []
                for idx in info['fixed_order_indices']:
                    if idx < len(current_words):
                        hz_order.append(current_words[idx].get('hz'))
                info['fixed_hz_order'] = hz_order
                del info['fixed_order_indices']
                updated = True
                
        if updated:
            save_json(DB_FILE, st.session_state.notebooks)

    def sync_and_get_ordered_words(nb_name, current_words):
        """
        Hàm cốt lõi: Khóa trật tự bằng Hán tự.
        - Lần đầu: Lấy 60 từ đầu -> shuffle, phần còn lại -> shuffle. Lưu mảng Hán tự.
        - Các lần sau: Lấy đúng trật tự đã lưu. Từ nào mới thêm sẽ bị ném xuống cuối.
        """
        if 'fixed_hz_order' not in st.session_state.notebooks[nb_name]:
            st.session_state.notebooks[nb_name]['fixed_hz_order'] = []
            
        saved_hzs = st.session_state.notebooks[nb_name]['fixed_hz_order']
        current_dict = {w['hz']: w for w in current_words}
        need_save = False
        
        # 1. Khởi tạo lần đầu
        if not saved_hzs and current_words:
            sorted_words = current_words
            part1 = [w['hz'] for w in sorted_words[:60]]
            part2 = [w['hz'] for w in sorted_words[60:]]
            random.shuffle(part1)
            random.shuffle(part2)
            
            saved_hzs = part1 + part2
            st.session_state.notebooks[nb_name]['fixed_hz_order'] = saved_hzs
            need_save = True

        # 2. Quét xem có từ nào mới được thêm vào không
        saved_set = set(saved_hzs)
        new_hzs = [w['hz'] for w in current_words if w['hz'] not in saved_set]
        if new_hzs:
            random.shuffle(new_hzs) # Xáo trộn đám từ mới
            saved_hzs.extend(new_hzs) # Nối vào đuôi, không làm hỏng Set cũ
            st.session_state.notebooks[nb_name]['fixed_hz_order'] = saved_hzs
            need_save = True
            
        if need_save:
            save_json(DB_FILE, st.session_state.notebooks)
            
        # 3. Trả về mảng words hoàn chỉnh theo đúng trật tự Hán tự đã khóa
        ordered_words = []
        for hz in saved_hzs:
            if hz in current_dict: # Rất an toàn: Nếu bạn lỡ xóa từ trong list gốc, nó sẽ tự bỏ qua
                ordered_words.append(current_dict[hz])
                
        return ordered_words

    # --- 1. HÀM TẠO QUIZ ---
    def get_smart_quiz(ordered_words, start_idx=0, end_idx=None):
        if end_idx is None: end_idx = len(ordered_words)
        selected_words = ordered_words[start_idx:end_idx]
        
        quiz_pool = []
        for w in selected_words:
            quiz_pool.append({'q': w['hz'].capitalize(), 'a': w['vn'], 'f': w, 'type': 'hz_vn'})
            quiz_pool.append({'q': w['vn'].capitalize(), 'a': w['hz'], 'f': w, 'type': 'vn_hz'})
        
        random.shuffle(quiz_pool) # Chỉ xáo trộn câu hỏi bên trong Set lúc làm bài
        return quiz_pool

    # Chạy dọn rác ngay khi vào trang
    migrate_to_hz_order()
    
    # --- UI HEADER ---
    col1, col2 = st.columns([6, 1])
    col1.title(f"🚀 Làm tí HSK [{user}]")
    if col2.button("Đăng xuất"):
        st.session_state.session["remembered"] = None
        save_json(SESSION_FILE, st.session_state.session)
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    # --- CÀI ĐẶT & LỊCH SỬ ---
    with st.expander("🎨 Cài đặt & Lịch sử"):
        c_th, c_his, c_download = st.columns(3)
        with c_th:
            theme_choice = st.selectbox("Giao diện:", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme_name))
            if theme_choice != st.session_state.theme_name:
                st.session_state.theme_name = theme_choice
                st.session_state.users[user]["theme"] = theme_choice
                save_json(USERS_FILE, st.session_state.users)
                st.rerun()
        with c_his:
            total_learned = len([k for k, v in st.session_state.progress["words"].items() if v != 0])
            st.metric("Số từ đã tiếp xúc", total_learned)
        with open("user_data/notebooks.json", "rb") as f:
            c_download.download_button(
                label="Tải dữ liệu JSON",
                data=f,
                file_name="notebooks.json",
                mime="application/json"
            )

    # --- ADMIN: TẠO SỔ TAY ---
    if is_admin:
        with st.expander("🛠️ Tạo Sổ Tay (Admin Only)"):
            n_name = st.text_input("Tên sổ tay:")
            n_data = st.text_area("Dữ liệu (Hán - Py - Nghĩa...):", height=100)
            if st.button("Lưu Sổ Tay"):
                if n_name and n_data:
                    st.session_state.notebooks[n_name] = {
                        'words': parse_data(n_data), 
                        'updated_at': datetime.now().isoformat(), 
                        'last_accessed': datetime.now().isoformat(),
                        'fixed_hz_order': [] # Mảng rỗng, sẽ tự sinh khi load
                    }
                    save_json(DB_FILE, st.session_state.notebooks)
                    st.success("Đã tạo sổ tay!")
                    st.rerun()

    # --- DANH SÁCH SỔ TAY ---
    if st.session_state.notebooks:
        sorted_nbs = sorted(st.session_state.notebooks.items(), key=lambda x: str(x[1].get('last_accessed', '')), reverse=True)
        
        for idx, (name, info) in enumerate(sorted_nbs, 1):
            raw_words = info['words']
            # BƯỚC QUAN TRỌNG: Đồng bộ và lấy mảng từ vựng đã được khóa chặt trật tự
            ordered_words = sync_and_get_ordered_words(name, raw_words)
            
            sticker = ["📚", "🔥", "⚡", "🌟", "🧠"][idx % 5]
            
            with st.container():
                st.markdown(f"### {sticker} {name} <span style='font-size:0.5em; color:gray'>({len(ordered_words)} từ)</span>", unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
                
                # --- NÚT HỌC NGAY (Top 60) ---
                if c1.button("📖 Học ngay", key=f"std_{name}", use_container_width=True):
                    st.session_state.notebooks[name]['last_accessed'] = datetime.now().isoformat()
                    quiz = get_smart_quiz(ordered_words, 0, 60)
                    st.session_state.update({"qs": quiz, "curr_nb": f"{name} (Top 60)", "mode": "study", "idx": 0, "answered": False})
                    save_resume_state()
                    st.rerun()
                
                # --- NÚT XEM DANH SÁCH (Sắp xếp A-Z Pinyin) ---
                if c2.button("📑 Danh sách", key=f"vw_{name}", use_container_width=True):
                    st.session_state.view_nb = name if st.session_state.get('view_nb') != name else None
                    st.rerun()

                import unicodedata

                def remove_accents(input_str):
                    """Chuyển 'ā' thành 'a', 'ò' thành 'o' để sắp xếp chuẩn A-Z"""
                    if not isinstance(input_str, str):
                        return ""
                    # Chuẩn hóa Unicode về dạng NFD (tách chữ và dấu)
                    nfkd_form = unicodedata.normalize('NFKD', input_str)
                    # Chỉ giữ lại các ký tự không phải là dấu (non-spacing mark)
                    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

                if st.session_state.get('view_nb') == name:
                    with st.container():
                        st.markdown(f"#### 📖 Tra cứu từ vựng: {name}")
                        df_view = pd.DataFrame(raw_words)
                        
                        if not df_view.empty:
                            # TẠO CỘT TẠM ĐỂ SORT: Loại bỏ dấu và chuyển về chữ thường
                            df_view['sort_key'] = df_view['py'].apply(lambda x: remove_accents(x).lower())
                            
                            # Sắp xếp theo cột tạm đó
                            df_view = df_view.sort_values(by='sort_key').reset_index(drop=True)
                            df_view.index += 1
                            
                            # Hiển thị bảng (loại bỏ cột sort_key khi show)
                            st.dataframe(
                                df_view[['hz', 'py', 'vn']], 
                                column_config={
                                    "hz": "Hán tự",
                                    "py": "Pinyin",
                                    "vn": "Nghĩa Việt"
                                },
                                use_container_width=True, height=400
                            )
                        else:
                            st.info("Trống.")

                    if st.button("✖️ Đóng", key=f"close_view_{name}"):
                        st.session_state.view_nb = None
                        st.rerun()
            
                # --- QUẢN LÝ ADMIN: SỬA VÀ XÓA ---
                if is_admin:
                    if c3.button("🤕 Sửa", key=f"ed_{name}", use_container_width=True):
                        st.session_state.editing_nb = name if st.session_state.get("editing_nb") != name else None
                        st.rerun()
                    
                    conf_k = f"conf_del_{name}"
                    if not st.session_state.get(conf_k):
                        if c4.button("😵 Xóa", key=f"dl_{name}", use_container_width=True):
                            st.session_state[conf_k] = True
                            st.rerun()
                    else:
                        cy, cn = c4.columns(2)
                        if cy.button("✅", key=f"y_{name}"):
                            del st.session_state.notebooks[name]
                            save_json(DB_FILE, st.session_state.notebooks)
                            st.rerun()
                        if cn.button("❌", key=f"n_{name}"):
                            st.session_state[conf_k] = False
                            st.rerun()

                # --- FORM SỬA SỔ TAY ---
                if st.session_state.get("editing_nb") == name:
                    with st.form(key=f"f_edit_{name}"):
                        new_n = st.text_input("Tên mới:", value=name)
                        new_d = st.text_area("Dữ liệu:", value=format_to_text_6_cols(raw_words), height=250)
                        if st.form_submit_button("Lưu ✅"):
                            if new_n != name: 
                                st.session_state.notebooks.pop(name)
                            st.session_state.notebooks[new_n] = {
                                'words': parse_data(new_d), 
                                'updated_at': datetime.now().isoformat(),
                                'last_accessed': datetime.now().isoformat(),
                                # ĐẶC BIỆT: Bê nguyên trật tự cũ sang, không reset. Hàm sync sẽ lo phần còn lại.
                                'fixed_hz_order': info.get('fixed_hz_order', []) 
                            }
                            save_json(DB_FILE, st.session_state.notebooks)
                            st.session_state.editing_nb = None
                            st.rerun()

                # --- CHIA SET ---
                with st.expander("🧩 Chia nhỏ bài học (Smart Sets)"):
                    total_w = len(ordered_words)
                    step_opts = get_step_options(total_w)
                    chunk = st.select_slider("Số từ mỗi Set:", options=step_opts, key=f"s_{name}", value=min(10, total_w))
                    
                    num_sets = (total_w + chunk - 1) // chunk

                    for r_idx in range(0, num_sets, 3):
                        cols = st.columns(3)
                        for c_idx in range(3):
                            s_idx = r_idx + c_idx
                            if s_idx < num_sets:
                                start_i = s_idx * chunk
                                end_i = min(start_i + chunk, total_w)
                                
                                # Cắt trực tiếp từ mảng đã khóa trật tự
                                subset = ordered_words[start_i:end_i]
                                
                                mastered = sum(1 for w in subset if st.session_state.progress["words"].get(w['hz'], 0) >= 3)
                                rate = mastered / len(subset) if subset else 0
                                color = "#22c55e" if rate >= 0.8 else ("#3b82f6" if rate >= 0.4 else "#475569")
                                
                                btn_k = f"btn_set_{name}_{start_i}"
                                st.markdown(f"<style>button[key='{btn_k}']{{background:{color}!important; color:white!important; min-height:4rem;}}</style>", unsafe_allow_html=True)
                                
                                if cols[c_idx].button(f"Set {s_idx+1}\n({start_i+1}-{end_i})\n✅ {mastered}/{len(subset)}", key=btn_k, use_container_width=True):
                                    quiz = get_smart_quiz(ordered_words, start_i, end_i)
                                    st.session_state.update({
                                        "qs": quiz, 
                                        "curr_nb": f"{name} ({start_i} -> {end_i})", 
                                        "mode": "study", "idx": 0, "answered": False
                                    })
                                    save_resume_state()
                                    st.rerun()
                                    
# --- UI ÔN TẬP (MOBI-OPTIMIZED) ---
elif st.session_state.mode == "study":
    total = len(st.session_state.qs)
    curr_idx = st.session_state.idx
    
    # --- 1. CSS TỐI ƯU GIAO DIỆN ---
    st.markdown(f"""
        <style>
        /* Làm đậm thanh Progress */
        div[data-testid="stProgress"] > div > div > div > div {{
            background-color: {t['main']} !important; height: 12px !important;
        }}
        /* Container đáp án chia 2 phần */
        .answer-card {{
            display: flex; flex-direction: row; gap: 12px;
            padding: 12px !important; align-items: flex-start; margin-top: 10px;
        }}
        .ans-left {{ 
            flex: 1; border-right: 1px solid {t['border']}; 
            padding-right: 10px; text-align: center;
        }}
        .ans-right {{ flex: 1.5; font-size: 0.85rem; padding-left: 5px; }}
        /* Ép header 1 dòng */
        .study-header {{
            display: flex; justify-content: space-between; align-items: center;
            flex-wrap: nowrap; gap: 10px; margin-bottom: 5px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- 2. HEADER: Tên chủ đề + STT + Nút Thoát ---
    st.markdown(f'<div class="study-header">', unsafe_allow_html=True)
    col_h, col_ex = st.columns([4, 1])
    with col_h:
        st.markdown(f"#### 📖 {st.session_state.curr_nb.upper()} <span style='font-size:0.7em; color:gray'>({curr_idx+1}/{total})</span>", unsafe_allow_html=True)
    with col_ex:
        if st.button("✖", help="Thoát", use_container_width=True):
            st.session_state.mode = "manage"
            st.session_state.progress["resume_state"] = None
            sync_progress()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if curr_idx < total:
        q = st.session_state.qs[curr_idx]
        st.progress((curr_idx) / total)
        
        # Câu hỏi to, rõ ràng
        st.markdown(f'<div class="question-container"><h3 style="margin:0; font-size:1.8rem; text-align:center; font-weight: 600">{q["q"]}</h3></div>', unsafe_allow_html=True)
        
        # --- 3. INPUT & NÚT KIỂM TRA (Nút nằm bên trái) ---
        # Tỷ lệ [1, 4] để nút Check nhỏ và nằm bên trái, nếu màn hình quá hẹp sẽ tự xuống dòng
        st.markdown(f"""
            <style>
            /* Ép nút Primary có nền màu chủ đạo, chữ trắng, không bị nền trắng */
            .stButton > button[data-testid="baseButton-primary"] {{
                background-color: {t['main']} !important;
                color: white !important;
                border: none !important;
                width: 100% !important;
                height: 3rem !important;
            }}
            /* Hiệu ứng khi di chuột */
            .stButton > button[data-testid="baseButton-primary"]:hover {{
                opacity: 0.9;
                color: white !important;
            }}
            </style>
        """, unsafe_allow_html=True)
        with st.form(key=f"study_form_{curr_idx}", border=False):
            c_btn, c_input = st.columns([1, 4])
            
            with c_input:
                u_ans = st.text_input(
                    "Nhập đáp án:", 
                    key=f"ans_{curr_idx}", 
                    label_visibility="collapsed", 
                    placeholder="Gõ câu trả lời..."
                ).strip()

            with c_btn:
                if not st.session_state.get('answered'):
                    # Dùng form_submit_button để click 1 phát ăn ngay
                    # type="primary" sẽ làm nút có màu nền (không bị nền trắng viền xanh)
                    check_clicked = st.form_submit_button("✅", type="primary")
                else:
                    # Sau khi trả lời, nút Tiếp theo thế chỗ
                    if st.form_submit_button("➡️", type="primary"):
                        st.session_state.idx += 1
                        st.session_state.answered = False
                        save_resume_state()
                        st.rerun()

        # --- LOGIC XỬ LÝ (Nằm ngoài Form hoặc check biến check_clicked) ---
        if not st.session_state.get('answered') and check_clicked:
            if not u_ans:
                st.warning("Nhập từ đã nhé!")
            else:
                st.session_state.answered = True
                is_ok = (q['a'].lower() in u_ans.lower()) or (u_ans.lower() in q['a'].lower() and len(u_ans) > 0)
                st.session_state.is_correct = is_ok
                
                hz = q['f']['hz']
                st.session_state.progress["words"][hz] = st.session_state.progress["words"].get(hz, 0) + (1 if is_ok else -1)
                save_resume_state()
                st.rerun()

        # --- 4. CONTAINER ĐÁP ÁN (CHIA 2 PHẦN) ---
        if st.session_state.get('answered'):
            if st.session_state.is_correct: 
                st.success("🎉 Chính xác!")
            else: 
                st.error(f"Sai rồi! Đáp án: **{q['a']}**")
                st.session_state.qs.append(st.session_state.qs[curr_idx])
            
            # Nội dung ví dụ bên phải
            ex_content = f"""
                <div class="ans-right">
                    <b style="color: {t['main']}">Ví dụ:</b><br>
                    <span style="font-size: 1rem;">{q['f']['ex_hz']}</span><br>
                    <i style="color: gray; font-size: 0.8rem;">{q['f']['ex_py']}</i><br>
                    <span>{q['f']['ex_vn']}</span>
                </div>
            """ if q['f']['ex_hz'] else '<div class="ans-right"><i>(Không có ví dụ)</i></div>'

            # Card hiển thị chi tiết (Không còn nút Tiếp theo ở dưới này nữa)
            st.markdown(f"""
                <div class="glass-box answer-card">
                    <div class="ans-left">
                        <h2 style="margin:0; color: {t['main']}">{q['f']['hz']}</h2>
                        <div style="font-size: 1.1rem; font-weight: bold;">{q['f']['py']}</div>
                        <div style="font-size: 0.9rem; color: gray;">{q['f']['vn'].capitalize()}</div>
                    </div>
                    {ex_content}
                </div>
            """, unsafe_allow_html=True)

        auto_focus()
    else:
        st.balloons()
        st.success("Hoàn thành bài học!")
        if st.button("Về Menu chính", use_container_width=True):
            st.session_state.mode = "manage"
            st.rerun()
  
  
  
  
            