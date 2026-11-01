# EduMind AI

Dashboard Streamlit cho học sinh lớp 6–12: học tập và ôn thi, chăm sóc tinh thần, khám phá hướng đi tương lai.

## Chạy ứng dụng

Yêu cầu Python 3.10 trở lên. Tại thư mục dự án:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

`main.py` chạy cùng ứng dụng để tương thích lệnh khởi động cũ. Giữ file `.env` đang có, hoặc tạo `.env` theo `.env.example`. Có thể cấu hình tương đương qua `.streamlit/secrets.toml`. Khi chưa có API key, giao diện, tài khoản và lịch sử vẫn hoạt động; thao tác gửi AI bị vô hiệu hóa.

Chế độ Nhanh mặc định dùng `gemini-3.1-flash-lite`, còn Tư duy dùng `gemini-3.6-flash`; `gemini-2.5-flash` là model dự phòng. Có thể đặt một model qua `GEMINI_FAST_MODEL` / `GEMINI_THINKING_MODEL`, hoặc danh sách phân tách bằng dấu phẩy qua `GEMINI_FAST_MODELS` / `GEMINI_THINKING_MODELS`. SDK tạo client riêng cho từng yêu cầu và tự loại API key/model bị khai báo trùng.

Ứng dụng kiểm tra kết nối Gemini khi phiên bắt đầu và hiển thị trạng thái trong sidebar. Lỗi mạng, timeout, xác thực, quota, model không tồn tại và lỗi nhà cung cấp có thông báo riêng. Lỗi tạm thời được thử tối đa ba lần qua model chính/dự phòng; câu hỏi chưa có phản hồi vẫn được giữ để người dùng thử lại mà không tạo bản sao.

Giải bài bằng ảnh yêu cầu đăng nhập và mặc định có 3 lượt/tài khoản/ngày (theo ngày Việt Nam). Có thể đặt `EDUMIND_IMAGE_DAILY_LIMIT` trong `.env` hoặc Streamlit secrets, giá trị từ 1 đến 100. Hạn mức được kiểm tra và giữ chỗ nguyên tử trong SQLite trước khi gọi Gemini; khi hết lượt, giao diện ẩn chức năng chọn ảnh. Một lần gửi ảnh được tính lượt kể cả khi dịch vụ AI lỗi. Ảnh JPG/JPEG/PNG tối đa 10 MB và 20 megapixel; ảnh được xử lý trong bộ nhớ và không lưu vào lịch sử. Chỉ gửi một request Gemini cho mỗi lần đặt chỗ, không tự retry hoặc tự đổi model cho ảnh. Hạn mức này kiểm soát mức dùng của ứng dụng, không đọc quota còn lại phía Gemini; lỗi 429 của provider vẫn có thể xảy ra. Camera trên thiết bị cần trình duyệt hỗ trợ quyền camera và kết nối HTTPS.

Chọn giao diện trong menu **⋮ → Settings → Theme**. Cả bảng màu Sáng và Tối được cấu hình trong `.streamlit/config.toml`; sidebar tự thu gọn theo màn hình nhỏ.

Không gian **Công cụ học tập** mở bảng biến thiên/đồ thị và GeoGebra trong khung khi website cho phép, đồng thời luôn có liên kết mở tab mới. Symbolab và PhET được mở bên ngoài do chính sách iframe của các website này không cho nhúng vào EduMind.

Prompt học tập hướng dẫn AI bám Chương trình Giáo dục phổ thông 2018 và không đoán các cập nhật/chính sách năm học 2026–2027. EduMind hiện không truy xuất trực tiếp văn bản pháp luật mới trong lúc trả lời; khi hỏi quy định mới, AI được hướng dẫn nói rõ chưa thể xác minh trực tuyến và chỉ nguồn Bộ GD&ĐT (`moet.gov.vn`) cùng Cơ sở dữ liệu quốc gia về văn bản pháp luật (`vbpl.vn`). Đây là giới hạn có chủ ý, không phải bảo đảm rằng kiến thức của mô hình đã cập nhật mọi thay đổi.

Nguồn Bộ GD&ĐT để người dùng đối chiếu: [Danh mục văn bản quy phạm pháp luật](https://moet.gov.vn/van-ban/van-ban-quy-pham-phap-luat) và [chuyên mục Chương trình giáo dục phổ thông](https://moet.gov.vn/tin-tuc-cot-phai/chuong-trinh-giao-duc-pho-thong). Danh mục thay đổi theo thời gian; ứng dụng không tự tải hay diễn giải văn bản mới.

## Tài khoản và lịch sử

- Đăng ký bằng email và mật khẩu tối thiểu 8 ký tự; mật khẩu được hash bằng Argon2id. Hiện chưa xác minh email và chưa có khôi phục mật khẩu qua email.
- Tài khoản cũ: chọn **Đăng nhập / Đăng ký → Tài khoản cũ**, nhập tên và mật khẩu cũ rồi bổ sung email. ID tài khoản và lịch sử được giữ, hash SHA-256 cũ được nâng cấp khi xác thực thành công.
- Khách dùng Nhanh và lịch sử tạm trong phiên. Tư duy yêu cầu đăng nhập ở cả ba chức năng. Sau khi đăng nhập, cuộc trò chuyện khách đang mở và bản nháp được giữ; học tập/hướng nghiệp chỉ được nhập vào lịch sử tài khoản khi chọn lưu.
- Hội thoại học tập và hướng nghiệp mới của tài khoản tự lưu. Tâm lí mặc định không lưu: bật lưu sẽ lưu toàn bộ hội thoại đang mở, tắt sẽ dừng ghi tiếp. Bản đã lưu vẫn tồn tại đến khi người dùng xóa; khi đăng nhập lại, tâm lí tiếp tục mặc định tắt lưu.
- Tìm kiếm theo tiêu đề và nội dung; chọn hội thoại để khôi phục chức năng/bộ lọc, dùng menu bên cạnh để đổi tên hoặc xóa có xác nhận.

Dữ liệu lưu tại SQLite trên máy chủ. Nội dung được gửi đến Gemini để tạo phản hồi; chế độ tạm chỉ có nghĩa là ứng dụng không ghi cuộc trò chuyện đó vào SQLite. Không chia sẻ file database hoặc các bản sao lưu như mã nguồn.

## Dữ liệu và migration

Database chính là `edumind_history.db`; có thể thay bằng `EDUMIND_DB_PATH`. Lần chạy đầu nâng schema bằng transaction và tạo bản sao `<tên-db>.backup-<thời-gian-UTC>.db` trước khi thay một database đã có bảng. Migration có phiên bản và chạy lặp lại an toàn. Chat cũ thiếu thời gian thuộc nhóm **Cũ hơn**; chat thiếu chủ sở hữu không được gán cho bất kỳ tài khoản nào. `edu.db`, `edumind_data.db` và bảng `health_log` cũ không bị nhập, xóa hoặc thay nội dung.

Trước khi khôi phục bản sao, dừng Streamlit, giữ thêm một bản của database hiện tại và dùng bản sao tương ứng cùng phiên bản mã nguồn. Thư mục database phải có quyền ghi và được giữ bền vững khi triển khai.

## Cấu trúc

- `edumind/auth.py`, `storage.py`: xác thực, chuyển tài khoản cũ, migration và truy vấn theo chủ sở hữu.
- `edumind/models.py`: kiểu hội thoại, chức năng, chế độ và ngữ cảnh yêu cầu AI.
- `edumind/catalog.py`: danh mục gợi ý có thể chỉnh sửa; không phải mục lục đầy đủ mọi bộ sách.
- `edumind/ai.py`: quyền dùng Tư duy, prompt theo chức năng, nội dung đa phương thức, hội thoại nhiều lượt và xử lý lỗi Gemini.
- `edumind/storage.py`: migration SQLite, lịch sử theo chủ sở hữu và bộ đếm quota ảnh theo ngày.
- `edumind/ui.py`: dashboard, biểu mẫu, lịch sử, công cụ học tập, camera/thư viện ảnh và các luồng tương tác.

## Kiểm thử

Hướng dẫn chi tiết từ cấu trúc code và chạy trên Windows đến GitHub, cấu hình secrets và triển khai Streamlit có trong [QUY_TRINH_PHAT_TRIEN_EDUMIND.docx](QUY_TRINH_PHAT_TRIEN_EDUMIND.docx).

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q --basetemp=.test-baseline
```

Tests dùng database tạm và Gemini giả lập, không dùng khóa thật hoặc gửi nội dung tới nhà cung cấp. Bao gồm migration/sao lưu, quota ảnh theo tài khoản/ngày và giao dịch đồng thời, xử lý ảnh, kiểm soát request đa phương thức, Argon2 và tài khoản cũ, phân quyền hai tài khoản, lịch sử, retry không trùng, giữ bản nháp, danh mục lớp/môn, ba bước hướng nghiệp và đồng ý lưu tâm lí.

Kiểm tra giao diện khi phát hành: desktop và màn hình rộng 390px, cả Sáng/Tối; xem dashboard, form tài khoản, danh mục nhập thủ công, hội thoại dài/công thức, menu lịch sử và thông báo lỗi. Kiểm tra không tràn ngang, chữ/nút đọc rõ và ô nhập luôn tiếp cận được. Cần thêm một lượt thử Gemini thật với cấu hình triển khai để xác nhận quyền model/quota; kiểm thử tự động không thay thế bước này.

## Xử lý sự cố Gemini

- **Không kết nối được:** tiến trình chạy Streamlit cần được phép mở HTTPS tới `generativelanguage.googleapis.com:443`. Giao diện vẫn có thể mở bình thường dù kết nối này bị chặn.
- **API key không hợp lệ/chưa có quyền:** kiểm tra key và quyền model trong Google AI Studio; ứng dụng không ghi key hoặc nội dung câu hỏi vào log lỗi.
- **Hết quota/giới hạn tốc độ:** đợi hạn mức phục hồi hoặc kiểm tra quota API.
- **Model không tồn tại:** kiểm tra tên model trong `.env`; model dự phòng vẫn được thử tự động.
- **Gemini quá tải:** dùng nút **Thử trả lời lại**; tin nhắn người dùng không bị thêm lần nữa.

Khi chạy ứng dụng từ môi trường sandbox hoặc công cụ tự động hóa, hãy bảo đảm tiến trình Streamlit cũng được cấp quyền mạng. Việc chỉ cấp mạng cho một lệnh kiểm tra riêng không cấp mạng cho server đang chạy.
