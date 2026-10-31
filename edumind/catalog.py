"""A small editable catalogue of common topics, not a textbook index."""
MANUAL = "Nhập thủ công…"
TASKS = ["Gợi ý từng bước", "Giải chi tiết", "Luyện bài tương tự", "Lập kế hoạch ôn tập"]

MATH = {
    6: {"Số tự nhiên và số nguyên": ["Thứ tự thực hiện phép tính", "Ước và bội", "Bài toán thực tế"], "Phân số và số thập phân": ["Tính toán phân số", "Tỉ số phần trăm"], "Hình học trực quan": ["Chu vi và diện tích", "Tính đối xứng"]},
    7: {"Số hữu tỉ và số thực": ["Tính giá trị biểu thức", "Tìm x"], "Tỉ lệ thức và đại lượng tỉ lệ": ["Tỉ lệ thuận", "Tỉ lệ nghịch"], "Tam giác": ["Chứng minh bằng nhau", "Quan hệ cạnh và góc"]},
    8: {"Đa thức và hằng đẳng thức": ["Phân tích thành nhân tử", "Rút gọn biểu thức"], "Phương trình bậc nhất": ["Giải phương trình", "Bài toán bằng phương trình"], "Tứ giác và tam giác đồng dạng": ["Chứng minh hình học", "Tính độ dài"]},
    9: {"Căn thức": ["Rút gọn căn thức", "Tính giá trị biểu thức"], "Phương trình và hệ phương trình": ["Giải hệ", "Phương trình bậc hai", "Bài toán thực tế"], "Đường tròn và hệ thức lượng": ["Chứng minh hình học", "Tính góc và độ dài"]},
    10: {"Mệnh đề và tập hợp": ["Các phép toán tập hợp", "Mệnh đề có điều kiện"], "Hàm số bậc hai": ["Khảo sát đồ thị", "Bất phương trình bậc hai"], "Vectơ và tọa độ": ["Tính toán vectơ", "Phương trình đường thẳng"], "Tổ hợp và xác suất": ["Quy tắc đếm", "Xác suất cổ điển"]},
    11: {"Hàm số lượng giác": ["Phương trình lượng giác", "Biến đổi lượng giác"], "Dãy số": ["Cấp số cộng", "Cấp số nhân"], "Giới hạn và đạo hàm": ["Tính giới hạn", "Tính đạo hàm"], "Quan hệ trong không gian": ["Song song", "Vuông góc"]},
    12: {"Ứng dụng đạo hàm": ["Khảo sát hàm số", "Cực trị và tối ưu"], "Nguyên hàm và tích phân": ["Tính tích phân", "Diện tích và thể tích"], "Vectơ và tọa độ không gian": ["Mặt phẳng", "Đường thẳng", "Mặt cầu"], "Xác suất và thống kê": ["Xác suất có điều kiện", "Phân tích số liệu"]},
}


def subjects(grade):
    science = ["Khoa học tự nhiên", "Lịch sử và Địa lí", "Giáo dục công dân"] if grade <= 9 else ["Vật lí", "Hóa học", "Sinh học", "Lịch sử", "Địa lí", "Giáo dục kinh tế và pháp luật"]
    return ["Toán", "Ngữ văn", "Tiếng Anh", *science, "Tin học", MANUAL]


def topics(grade, subject):
    if subject == "Toán":
        return MATH[grade]
    advanced = grade >= 10
    catalog = {
        "Ngữ văn": {"Đọc hiểu văn bản": ["Phân tích chi tiết", "Biện pháp tu từ", "Thông điệp văn bản"], "Viết": ["Nghị luận xã hội", "Phân tích tác phẩm", "Lập dàn ý"]},
        "Tiếng Anh": {"Ngữ pháp": ["Thì và cấu trúc câu", "Câu điều kiện", "Câu bị động"], "Đọc hiểu và từ vựng": ["Đọc tìm ý chính", "Từ vựng theo ngữ cảnh"], "Viết": ["Viết đoạn văn", "Viết lại câu"]},
        "Khoa học tự nhiên": {"Chất và sự biến đổi": ["Giải thích hiện tượng", "Tính toán cơ bản"], "Năng lượng và sự biến đổi": ["Phân tích hiện tượng", "Bài tập định lượng"], "Vật sống": ["Giải thích quá trình", "So sánh và phân loại"]},
        "Vật lí": {"Cơ học" if grade == 10 else "Điện và sóng" if grade == 11 else "Nhiệt học và vật lí hạt nhân": ["Phân tích hiện tượng", "Vận dụng công thức", "Đọc đồ thị"]},
        "Hóa học": {"Cấu tạo chất và liên kết" if grade == 10 else "Cân bằng và hóa hữu cơ" if grade == 11 else "Hợp chất hữu cơ và kim loại": ["Viết phương trình phản ứng", "Tính theo phương trình", "Nhận biết chất"]},
        "Sinh học": {"Sinh học tế bào" if grade == 10 else "Sinh học cơ thể" if grade == 11 else "Di truyền và sinh thái": ["Giải thích cơ chế", "Phân tích thí nghiệm", "Vận dụng kiến thức"]},
        "Lịch sử và Địa lí": {"Lịch sử Việt Nam và thế giới": ["Dòng thời gian", "Nguyên nhân và kết quả"], "Địa lí tự nhiên và dân cư": ["Đọc bản đồ", "Phân tích bảng số liệu"]},
        "Lịch sử": {"Lịch sử Việt Nam": ["Phân tích sự kiện", "So sánh giai đoạn"], "Lịch sử thế giới": ["Nguyên nhân và kết quả", "Liên hệ lịch sử"]},
        "Địa lí": {"Địa lí tự nhiên": ["Phân tích bản đồ", "Giải thích hiện tượng"], "Kinh tế và dân cư": ["Đọc biểu đồ", "Phân tích số liệu"]},
        "Tin học": {"Lập trình" if advanced else "Tư duy thuật toán": ["Thiết kế thuật toán", "Đọc và sửa chương trình"], "Ứng dụng và dữ liệu": ["Giải quyết tình huống", "Tổ chức dữ liệu"]},
        "Giáo dục công dân": {"Đạo đức và kỹ năng sống": ["Phân tích tình huống", "Liên hệ bản thân"], "Quyền và trách nhiệm": ["Nhận diện hành vi", "Xử lý tình huống"]},
        "Giáo dục kinh tế và pháp luật": {"Hoạt động kinh tế": ["Phân tích tình huống", "Liên hệ thực tiễn"], "Pháp luật và công dân": ["Nhận diện quyền và nghĩa vụ", "Phân tích tình huống"]},
    }
    return catalog.get(subject, {})
