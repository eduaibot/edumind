from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from edumind.ai import AIErrorKind, AIHealth, AIService, AIUnavailable
from edumind.auth import Auth
from edumind.catalog import MANUAL, TASKS
from edumind.models import Feature
from edumind.storage import Store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    import edumind.ui as ui

    monkeypatch.setattr(ui, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("EDUMIND_DB_PATH", str(tmp_path / "app.db"))
    for name in ("GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"):
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("GEMINI_API_KEY_1", "fake-for-tests")
    calls = []

    def fake_answer(self, request, user=None):
        calls.append((request, user))
        return "Phản hồi kiểm thử cho " + request.text

    monkeypatch.setattr(AIService, "answer", fake_answer)
    monkeypatch.setattr(AIService, "check_connection", lambda self: AIHealth(True, "Gemini đã kết nối"))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert not at.exception
    return at, Store(tmp_path / "app.db"), calls


def button(at, label):
    return next(b for b in at.button if b.label == label)


def select(at, label):
    return next(s for s in at.selectbox if s.label == label)


def chat(at):
    return at.session_state["chats"][at.session_state["current"]]


def send(at, text):
    chat_id = chat(at).id
    next(a for a in at.text_area if a.label == "Tin nhắn của bạn").set_value(text).run()
    at.button(key=f"send_{chat_id}").click().run()
    assert not at.exception


def complete_wellbeing_checkin(at, mood="Lo lắng", situation="Chuyện học đang làm mình căng thẳng"):
    chat_id = chat(at).id
    at.radio(key=f"wellbeing_mood_{chat_id}").set_value(mood).run()
    at.button(key=f"wellbeing_next_{chat_id}_0").click().run()
    at.text_area(key=f"wellbeing_situation_{chat_id}").set_value(situation).run()
    at.button(key=f"wellbeing_next_{chat_id}_1").click().run()
    at.radio(key=f"wellbeing_intensity_{chat_id}").set_value("3 · Vừa").run()
    at.button(key=f"wellbeing_next_{chat_id}_2").click().run()
    at.radio(key=f"wellbeing_support_{chat_id}").set_value("Được lắng nghe").run()
    at.button(key=f"wellbeing_next_{chat_id}_3").click().run()
    at.run()
    assert not at.exception


def login_as_test_user(at, store):
    user = Auth(store).register("test@example.com", "password123")
    at.session_state["user"] = user
    at.run()
    return user


def test_dashboard_navigation_and_no_api_key(app_env, monkeypatch):
    at, store, calls = app_env
    assert at.title[0].value == "Mỗi ngày, tiến thêm một bước."
    monkeypatch.setenv("GEMINI_API_KEY_1", "")
    for feature in Feature:
        at.radio(key="nav").set_value(feature.value).run()
        assert not at.exception
        if feature == Feature.WELLBEING:
            assert button(at, "Tiếp tục").disabled
            assert all(b.label != "Gửi" for b in at.button)
        else:
            assert button(at, "Gửi").disabled
    button(at, "Đăng nhập / Đăng ký").click().run()
    assert at.text_input(key="login_email")
    assert not calls


@pytest.mark.parametrize("feature", list(Feature))
def test_guest_thinking_block_and_keeps_draft(app_env, feature):
    at, store, calls = app_env
    at.radio(key="nav").set_value(feature.value).run()
    at.radio(key="mode").set_value("thinking").run()
    if feature == Feature.WELLBEING:
        complete_wellbeing_checkin(at)
    send(at, "Nội dung đang soạn")
    assert calls == [] and chat(at).messages == []
    assert next(a for a in at.text_area if a.label == "Tin nhắn của bạn").value == "Nội dung đang soạn"
    at.radio(key="mode").set_value("fast").run()
    button(at, "Gửi").click().run()
    assert len(calls) == 1 and len(chat(at).messages) == 2
    assert store.path.exists()
    with store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0] == 0


def test_signup_preserves_guest_draft_and_auto_saves_study(app_env):
    at, store, calls = app_env
    at.radio(key="nav").set_value("study").run()
    send(at, "Giải giúp mình x+1=2")
    guest_id = chat(at).id
    next(a for a in at.text_area if a.label == "Tin nhắn của bạn").set_value("Bản nháp tiếp theo").run()
    at.radio(key="mode").set_value("thinking").run()
    button(at, "Đăng nhập / Đăng ký").click().run()
    at.radio(key="auth_tab").set_value("Đăng ký").run()
    at.text_input(key="register_email").set_value("new@example.com")
    at.text_input(key="register_password").set_value("password123")
    at.text_input(key="register_confirm").set_value("password123")
    button(at, "Tạo tài khoản").click().run()
    assert not at.exception
    user = at.session_state["user"]
    assert user.email == "new@example.com" and chat(at).id == guest_id
    assert at.radio(key="mode").value == "thinking"
    assert next(a for a in at.text_area if a.label == "Tin nhắn của bạn").value == "Bản nháp tiếp theo"
    assert store.get_chat(user.id, guest_id).messages[0]["content"] == "Giải giúp mình x+1=2"
    assert chat(at).save_enabled is True
    button(at, "Đăng xuất").click().run()
    assert not at.exception
    assert at.session_state["user"] is None and at.session_state["chats"] == {}
    assert at.session_state["drafts"] == {}


def test_login_failure_and_success(app_env):
    at, store, calls = app_env
    user = Auth(store).register("a@example.com", "password123")
    button(at, "Đăng nhập / Đăng ký").click().run()
    at.text_input(key="login_email").set_value("a@example.com")
    at.text_input(key="login_password").set_value("incorrect")
    button(at, "Đăng nhập").click().run()
    assert at.session_state["user"] is None and at.error
    at.text_input(key="login_password").set_value("password123")
    button(at, "Đăng nhập").click().run()
    assert not at.exception and at.session_state["user"].id == user.id


def test_study_filters_tasks_and_reopening_context(app_env):
    at, store, calls = app_env
    user = login_as_test_user(at, store)
    at.radio(key="nav").set_value("study").run()
    at.toggle(key=f"study_{chat(at).id}_setup_enabled").set_value(True).run()
    select(at, "Lớp").set_value(12).run()
    select(at, "Chủ đề").set_value("Nguyên hàm và tích phân").run()
    select(at, "Dạng bài").set_value("Tính tích phân").run()
    select(at, "Bạn muốn được hỗ trợ thế nào?").set_value(TASKS[0]).run()
    send(at, "Gợi ý cho mình bài tích phân")
    first_id = chat(at).id
    assert calls[-1][0].context["grade"] == 12
    assert calls[-1][0].context["exercise"] == "Tính tích phân"
    select(at, "Bạn muốn được hỗ trợ thế nào?").set_value(TASKS[2]).run()
    send(at, "Cho mình bài tương tự")
    assert len(calls[-1][0].history) == 2
    at.radio(key="nav").set_value("career").run()
    at.button(key=f"open_{first_id}").click().run()
    assert not at.exception and at.radio(key="nav").value == "study"
    assert select(at, "Lớp").value == 12 and select(at, "Chủ đề").value == "Nguyên hàm và tích phân"
    select(at, "Lớp").set_value(7).run()
    assert select(at, "Chủ đề").value == "Số hữu tỉ và số thực"
    select(at, "Môn học").set_value(MANUAL).run()
    next(i for i in at.text_input if i.label == "Nhập môn học").set_value("Công nghệ").run()
    next(i for i in at.text_input if i.label == "Nhập chủ đề").set_value("Thiết kế kỹ thuật").run()
    next(i for i in at.text_input if i.label == "Nhập dạng bài").set_value("Phân tích sản phẩm").run()
    select(at, "Bạn muốn được hỗ trợ thế nào?").set_value(TASKS[3]).run()
    next(i for i in at.text_input if i.label == "Mục tiêu ôn tập").set_value("Ôn cuối kỳ").run()
    button(at, "Tạo kế hoạch ôn tập").click().run()
    assert not at.exception
    assert calls[-1][0].context["subject"] == "Công nghệ"
    assert calls[-1][0].context["minutes_per_day"] == 45
    assert store.get_chat(user.id, first_id).metadata["task"] == TASKS[3]


def test_study_setup_is_optional_and_filters_request_context(app_env):
    at, store, calls = app_env
    at.radio(key="nav").set_value("study").run()
    chat_id = chat(at).id
    assert at.toggle(key=f"study_{chat_id}_setup_enabled").value is False
    send(at, "Mình muốn hỏi tự do")
    assert calls[-1][0].context == {"study_setup_enabled": False}
    at.toggle(key=f"study_{chat_id}_setup_enabled").set_value(True).run()
    select(at, "Lớp").set_value(12).run()
    send(at, "Giải theo chương trình lớp của mình")
    assert calls[-1][0].context["grade"] == 12
    at.toggle(key=f"study_{chat_id}_setup_enabled").set_value(False).run()
    send(at, "Quay lại chat tự do")
    assert "grade" not in calls[-1][0].context
    assert chat(at).metadata["grade"] == 12


def test_waiting_state_renders_before_ai_response(app_env, monkeypatch):
    import edumind.ui as ui

    at, store, calls = app_env
    original = ui.process_pending_request
    monkeypatch.setattr(ui, "process_pending_request", lambda *args, **kwargs: None)
    at.radio(key="nav").set_value("study").run()
    chat_id = chat(at).id
    next(a for a in at.text_area if a.label == "Tin nhắn của bạn").set_value("Câu hỏi đang chờ").run()
    at.button(key=f"send_{chat_id}").click().run()
    assert calls == [] and len(chat(at).messages) == 1
    assert at.session_state["pending_request"]["chat_id"] == chat_id
    assert at.button(key=f"send_{chat_id}").disabled
    assert any("AI đang suy nghĩ" in item.value for item in at.markdown)
    monkeypatch.setattr(ui, "process_pending_request", original)
    at.run()
    assert len(calls) == 1 and [m["role"] for m in chat(at).messages] == ["user", "assistant"]


def test_failure_retry_has_no_duplicate_and_uses_snapshot(app_env, monkeypatch):
    at, store, calls = app_env
    at.radio(key="nav").set_value("study").run()
    at.toggle(key=f"study_{chat(at).id}_setup_enabled").set_value(True).run()
    attempts = []

    def fail_once(self, request, user=None):
        attempts.append(request)
        if len(attempts) == 1:
            raise AIUnavailable(AIErrorKind.PROVIDER_UNAVAILABLE)
        return "Đã trả lời"

    monkeypatch.setattr(AIService, "answer", fail_once)
    send(at, "Câu hỏi cần giữ")
    assert len(chat(at).messages) == 1 and at.warning
    select(at, "Lớp").set_value(12).run()
    button(at, "Thử trả lời lại").click().run()
    assert not at.exception
    assert [m["role"] for m in chat(at).messages] == ["user", "assistant"]
    assert attempts[1].context["grade"] == attempts[0].context["grade"] == 9


def test_wellbeing_opt_in_stop_saving_and_delete(app_env):
    at, store, calls = app_env
    user = login_as_test_user(at, store)
    at.radio(key="nav").set_value("wellbeing").run()
    complete_wellbeing_checkin(at)
    assert chat(at).metadata["checkin_complete"] is True
    assert chat(at).metadata["mood"] == "Lo lắng"
    send(at, "Mình lo chuyện học")
    chat_id = chat(at).id
    assert not store.list_chats(user.id)
    send(at, "Nhất là môn toán")
    assert len(calls[-1][0].history) == 4
    at.toggle(key=f"mental_save_{chat_id}").set_value(True).run()
    assert len(store.get_chat(user.id, chat_id).messages) == 6
    at.toggle(key=f"mental_save_{chat_id}").set_value(False).run()
    send(at, "Tin này không lưu tiếp")
    assert len(store.get_chat(user.id, chat_id).messages) == 6
    assert len(chat(at).messages) == 8
    button(at, "Xóa phiên đang mở").click().run()
    assert store.get_chat(user.id, chat_id) is not None
    at.button(key="confirm_delete").click().run()
    assert not at.exception and store.get_chat(user.id, chat_id) is None


def test_wellbeing_guided_checkin_can_go_back_and_change_answer(app_env):
    at, store, calls = app_env
    at.radio(key="nav").set_value("wellbeing").run()
    chat_id = chat(at).id
    assert all(a.label != "Tin nhắn của bạn" for a in at.text_area)
    at.radio(key=f"wellbeing_mood_{chat_id}").set_value("Buồn").run()
    at.button(key=f"wellbeing_next_{chat_id}_0").click().run()
    at.button(key=f"wellbeing_back_{chat_id}_1").click().run()
    assert at.radio(key=f"wellbeing_mood_{chat_id}").value == "Buồn"
    at.radio(key=f"wellbeing_mood_{chat_id}").set_value("Mệt mỏi").run()
    complete_wellbeing_checkin(at, mood="Mệt mỏi")
    assert chat(at).metadata["mood"] == "Mệt mỏi"
    assert next(a for a in at.text_area if a.label == "Tin nhắn của bạn")
    assert calls[-1][0].context["support"] == "Được lắng nghe"


def test_guest_has_one_chat_per_feature_and_new_chat_requires_login(app_env):
    at, store, calls = app_env
    ids = {}
    for feature in Feature:
        at.radio(key="nav").set_value(feature.value).run()
        ids[feature] = chat(at).id
    for feature in Feature:
        at.radio(key="nav").set_value(feature.value).run()
        assert chat(at).id == ids[feature]
    current_id = chat(at).id
    button(at, "Cuộc trò chuyện mới").click().run()
    assert at.session_state["current"] == current_id
    assert at.text_input(key="login_email")
    assert len([item for item in at.session_state["chats"].values() if item.owner is None]) == 3


def test_login_imports_all_guest_chats_with_wellbeing_opt_in(app_env):
    at, store, calls = app_env
    at.radio(key="nav").set_value("study").run()
    send(at, "Chat học của khách")
    study_id = chat(at).id
    at.radio(key="nav").set_value("wellbeing").run()
    complete_wellbeing_checkin(at)
    wellbeing_id = chat(at).id
    at.radio(key="nav").set_value("career").run()
    send(at, "Chat định hướng của khách")
    career_id = chat(at).id
    button(at, "Đăng nhập / Đăng ký").click().run()
    at.radio(key="auth_tab").set_value("Đăng ký").run()
    at.text_input(key="register_email").set_value("three@example.com")
    at.text_input(key="register_password").set_value("password123")
    at.text_input(key="register_confirm").set_value("password123")
    button(at, "Tạo tài khoản").click().run()
    user = at.session_state["user"]
    assert {study_id, wellbeing_id, career_id}.issubset(at.session_state["chats"])
    assert store.get_chat(user.id, study_id) is not None
    assert store.get_chat(user.id, career_id) is not None
    assert store.get_chat(user.id, wellbeing_id) is None
    assert at.session_state["chats"][wellbeing_id].save_enabled is False


def test_career_three_steps_and_save(app_env):
    at, store, calls = app_env
    user = login_as_test_user(at, store)
    at.radio(key="nav").set_value("career").run()
    prefix = f"career_{chat(at).id}_"
    at.number_input(key=prefix + "age").set_value(14).run()
    at.text_input(key=prefix + "interests").set_value("Vẽ và kể chuyện").run()
    at.text_area(key=prefix + "strengths").set_value("Quan sát tốt").run()
    select(at, "Lớp hiện tại *").set_value(8).run()
    at.text_input(key=prefix + "current_study_place").set_value("Đà Nẵng").run()
    at.text_input(key=prefix + "preferred_study_place").set_value("TP.HCM").run()
    at.text_input(key=prefix + "preferred_work_place").set_value("Làm việc từ xa").run()
    at.text_input(key=prefix + "preferred_work_environment").set_value("Sáng tạo").run()
    button(at, "Khám phá 3 hướng phù hợp").click().run()
    assert calls[-1][0].context["age"] == 14
    assert calls[-1][0].context["grade"] == 8
    assert calls[-1][0].context["preferred_work_place"] == "Làm việc từ xa"
    assert calls[-1][0].context["task"] == "Khám phá"
    select(at, "Bước tiếp theo").set_value("2 · So sánh hướng đi").run()
    at.text_input(key=prefix + "choices").set_value("Thiết kế, giáo dục, truyền thông").run()
    button(at, "So sánh các lựa chọn").click().run()
    assert calls[-1][0].context["task"] == "So sánh"
    select(at, "Bước tiếp theo").set_value("3 · Kế hoạch & trải nghiệm").run()
    at.text_input(key=prefix + "role").set_value("Thiết kế đồ họa").run()
    button(at, "Xây kế hoạch").click().run()
    assert calls[-1][0].context["months"] == 6
    button(at, "Thử một tình huống").click().run()
    send(at, "Mình sẽ hỏi rõ yêu cầu trước")
    assert calls[-1][0].context["task"] == "Trải nghiệm"
    assert len(calls[-1][0].history) == 8
    assert len(store.get_chat(user.id, chat(at).id).messages) == 10
    assert at.get("download_button")


def test_history_search_rename_delete_and_correct_chat_save(app_env):
    at, store, calls = app_env
    user = login_as_test_user(at, store)
    at.radio(key="nav").set_value("study").run()
    send(at, "Bài tập thứ nhất")
    first_id = chat(at).id
    button(at, "Cuộc trò chuyện mới").click().run()
    send(at, "Bài tập thứ hai")
    second_id = chat(at).id
    at.button(key=f"open_{first_id}").click().run()
    send(at, "Nội dung riêng của chat đầu")
    assert len(store.get_chat(user.id, first_id).messages) == 4
    assert len(store.get_chat(user.id, second_id).messages) == 2
    at.text_input(key="history_search").set_value("riêng của chat đầu").run()
    assert at.button(key=f"open_{first_id}")
    assert all(b.key != f"open_{second_id}" for b in at.button)
    at.button(key=f"rename_{first_id}").click().run()
    next(i for i in at.text_input if i.label == "Tên cuộc trò chuyện").set_value("Tên đã đổi")
    button(at, "Lưu tên").click().run()
    assert store.get_chat(user.id, first_id).title == "Tên đã đổi"
    at.button(key=f"delete_{first_id}").click().run()
    at.button(key="confirm_delete").click().run()
    assert not at.exception
    assert store.get_chat(user.id, first_id) is None and store.get_chat(user.id, second_id) is not None


def test_main_entrypoint_uses_same_app(app_env):
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=15).run()
    assert not at.exception
    assert at.title[0].value == "Mỗi ngày, tiến thêm một bước."


def test_legacy_account_conversion_form(app_env):
    import hashlib

    at, store, calls = app_env
    with store.connection() as conn:
        conn.execute("INSERT INTO users(username,password) VALUES(?,?)", ("oldname", hashlib.sha256(b"password123").hexdigest()))
    button(at, "Đăng nhập / Đăng ký").click().run()
    at.radio(key="auth_tab").set_value("Tài khoản cũ").run()
    at.text_input(key="legacy_identity").set_value("oldname")
    at.text_input(key="legacy_password").set_value("password123")
    at.text_input(key="legacy_email").set_value("converted@example.com")
    button(at, "Chuyển sang email").click().run()
    assert not at.exception and at.session_state["user"].id == "oldname"
    assert at.session_state["user"].email == "converted@example.com"


def test_failed_question_retry_after_reloading_saved_history(app_env, monkeypatch):
    at, store, calls = app_env
    user = login_as_test_user(at, store)
    at.radio(key="nav").set_value("study").run()
    at.toggle(key=f"study_{chat(at).id}_setup_enabled").set_value(True).run()

    def failing(self, request, user=None):
        raise AIUnavailable(AIErrorKind.PROVIDER_UNAVAILABLE)

    monkeypatch.setattr(AIService, "answer", failing)
    send(at, "Bài này chưa có phản hồi")
    chat_id = chat(at).id
    loaded = store.get_chat(user.id, chat_id)
    loaded.metadata["grade"] = 12
    at.session_state["chats"] = {chat_id: loaded}
    at.session_state["failure"] = None
    at.run()
    requests = []

    def success(self, request, user=None):
        requests.append(request)
        return "Đã xử lý"

    monkeypatch.setattr(AIService, "answer", success)
    button(at, "Thử trả lời lại").click().run()
    assert not at.exception
    assert requests[0].context["grade"] == 9
    assert len(store.get_chat(user.id, chat_id).messages) == 2
