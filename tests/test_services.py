import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import httpx
from google.genai import errors

from edumind.ai import AIErrorKind, AIService, AIUnavailable, LoginRequired, classify_exception, safety_response, system_instruction
from edumind.auth import Auth
from edumind.catalog import MANUAL, subjects, topics
from edumind.models import AIMode, AIRequest, Conversation, Feature, LOCAL_TZ, history_group
from edumind.storage import ImageQuotaExceeded, OwnershipError, Store


@pytest.fixture
def store(tmp_path):
    store = Store(tmp_path / "test.db")
    store.migrate()
    return store


def test_migration_backups_preserves_legacy_and_is_idempotent(tmp_path):
    path = tmp_path / "legacy.db"
    hashed = hashlib.sha256(b"oldpassword").hexdigest()
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE users(username TEXT PRIMARY KEY, password TEXT)")
        conn.execute("CREATE TABLE chats(id TEXT PRIMARY KEY, username TEXT, title TEXT, messages TEXT)")
        conn.execute("INSERT INTO users VALUES(?,?)", ("olduser", hashed))
        conn.execute("INSERT INTO chats VALUES(?,?,?,?)", ("oldchat", "olduser", "Bài tập cũ", json.dumps([{"role": "user", "content": "x+1=2"}])))
        conn.execute("CREATE TABLE health_log(note TEXT)")
        conn.execute("INSERT INTO health_log VALUES('retained')")
    store = Store(path)
    store.migrate()
    store.migrate()
    backups = list(tmp_path.glob("*.backup-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as conn:
        assert conn.execute("SELECT password FROM users").fetchone()[0] == hashed
    chat = store.get_chat("olduser", "oldchat")
    assert chat.feature == Feature.STUDY and chat.updated_at is None
    assert chat.messages[0]["content"] == "x+1=2"
    assert history_group(chat.updated_at) == "Cũ hơn"
    with store.connection() as conn:
        assert conn.execute("SELECT note FROM health_log").fetchone()[0] == "retained"
    auth = Auth(store)
    assert auth.authenticate("olduser", "wrong", legacy=True) is None
    user = auth.link_legacy_email("olduser", "oldpassword", " OLD@Example.com ")
    assert user.id == "olduser" and user.email == "old@example.com"
    assert auth.authenticate("old@example.com", "oldpassword").id == "olduser"
    assert store.get_chat(user.id, "oldchat") is not None
    with store.connection() as conn:
        assert conn.execute("SELECT password FROM users").fetchone()[0].startswith("$argon2id$")


def test_migration_handles_newer_incompatible_version_gracefully(tmp_path):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE users(username TEXT PRIMARY KEY, password TEXT)")
        conn.execute("PRAGMA user_version = 99")
    store = Store(path)
    store.migrate()
    with store.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    incompatible_backups = list(tmp_path.glob("*.incompatible-v99-*.db"))
    assert len(incompatible_backups) == 1


def test_registration_validation_and_duplicate_email(store):
    auth = Auth(store)
    for email, password in [("invalid", "longpassword"), ("a@b.com", "short")]:
        with pytest.raises(ValueError):
            auth.register(email, password)
    user = auth.register(" Student@Example.com ", "password123")
    assert auth.authenticate("STUDENT@example.com", "password123") == user
    assert auth.authenticate("student@example.com", "incorrect") is None
    with pytest.raises(ValueError, match="đã được"):
        auth.register("student@example.com", "anotherpassword")
    with store.connection() as conn:
        stored = conn.execute("SELECT password FROM users").fetchone()[0]
        assert stored.startswith("$argon2id$") and "password123" not in stored


def test_legacy_email_collision_keeps_ownership(store):
    auth = Auth(store)
    auth.register("existing@example.com", "password123")
    with store.connection() as conn:
        conn.execute("INSERT INTO users VALUES(?,?,NULL)", ("legacy", hashlib.sha256(b"oldpassword").hexdigest()))
    with pytest.raises(ValueError):
        auth.link_legacy_email("legacy", "oldpassword", "existing@example.com")
    with store.connection() as conn:
        assert conn.execute("SELECT email FROM users WHERE username='legacy'").fetchone()[0] is None


def test_owner_is_required_for_every_read_and_write(store):
    chat = Conversation(Feature.STUDY)
    chat.add_question("Câu hỏi riêng của A")
    store.save_chat("a", chat)
    assert len(store.list_chats("a")) == 1
    assert store.list_chats("b") == []
    assert store.get_chat("b", chat.id) is None
    forged = replace(chat, owner="b", title="overwritten")
    with pytest.raises(OwnershipError):
        store.save_chat("b", forged)
    with pytest.raises(OwnershipError):
        store.rename_chat("b", chat.id, "changed")
    with pytest.raises(OwnershipError):
        store.delete_chat("b", chat.id)
    for operation in [lambda: store.list_chats(""), lambda: store.get_chat("", chat.id), lambda: store.save_chat("", chat), lambda: store.delete_chat("", chat.id), lambda: store.rename_chat("", chat.id, "x")]:
        with pytest.raises(OwnershipError):
            operation()
    assert store.get_chat("a", chat.id).title == "Câu hỏi riêng của A"


def test_history_search_order_metadata_rename_and_delete(store):
    first = Conversation(Feature.STUDY, metadata={"grade": 12, "subject": "Toán", "topic": "Tích phân"})
    first.add_question("Hướng dẫn bài này")
    second = Conversation(Feature.CAREER)
    second.add_question("Mình thích vẽ")
    store.save_chat("a", first)
    store.save_chat("a", second)
    assert store.list_chats("a")[0].id == second.id
    assert store.list_chats("a", "THÍCH VẼ")[0].id == second.id
    store.rename_chat("a", first.id, "Ôn Toán")
    assert store.list_chats("a")[0].id == first.id
    assert store.get_chat("a", first.id).metadata == first.metadata
    with pytest.raises(ValueError):
        store.rename_chat("a", first.id, " ")
    store.delete_chat("a", first.id)
    assert store.get_chat("a", first.id) is None
    assert store.get_chat("a", second.id) is not None


def test_image_quota_is_atomic_per_owner_and_day(store):
    user_a = Auth(store).register("image-a@example.com", "password123")
    user_b = Auth(store).register("image-b@example.com", "password123")
    quota_day = "2026-11-01"

    def reserve():
        try:
            return store.reserve_image_quota(user_a.id, quota_day, 3)
        except ImageQuotaExceeded:
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: reserve(), range(10)))

    assert sum(result is not None for result in results) == 3
    assert store.image_quota_status(user_a.id, quota_day, 3) == (3, 0)
    assert store.image_quota_status(user_b.id, quota_day, 3) == (0, 3)
    assert store.image_quota_status(user_a.id, "2026-11-02", 3) == (0, 3)
    with pytest.raises(ImageQuotaExceeded):
        store.reserve_image_quota(user_a.id, quota_day, 3)
    with pytest.raises(OwnershipError):
        store.reserve_image_quota("", quota_day, 3)


@pytest.mark.parametrize("feature", list(Feature))
def test_thinking_authorization_precedes_all_provider_calls(feature):
    service = AIService(["test-only"])
    request = AIRequest(feature, AIMode.THINKING, "hello", [], {})
    with pytest.raises(LoginRequired):
        service.answer(request)
    with pytest.raises(AIUnavailable):
        AIService([]).answer(replace(request, mode=AIMode.FAST))


def test_provider_context_history_and_thinking_configuration():
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text="Phản hồi [SUG] hidden")
    manager = MagicMock()
    manager.__enter__.return_value = client
    request = AIRequest(Feature.STUDY, AIMode.THINKING, "Giúp mình", [{"role": "user", "content": "Câu trước"}, {"role": "assistant", "content": "Gợi ý"}], {"grade": 9, "task": "Gợi ý từng bước"})
    with patch("google.genai.Client", return_value=manager):
        assert AIService(["key"], thinking_models=["gemini-2.5-flash"]).answer(request, user=SimpleNamespace(id="a")) == "Phản hồi"
    args = client.models.generate_content.call_args.kwargs
    assert [c.role for c in args["contents"]] == ["user", "model", "user"]
    assert '"grade": 9' in args["contents"][-1].parts[0].text
    assert args["config"].thinking_config.thinking_budget == 8192


def test_image_request_is_multimodal_and_requires_login_before_provider():
    payload = b"png bytes used only by the fake provider"
    request = AIRequest(
        Feature.STUDY,
        AIMode.FAST,
        "Giải bài trong ảnh",
        [],
        {"grade": 8},
        payload,
        "image/png",
    )
    with patch("google.genai.Client") as constructor:
        with pytest.raises(LoginRequired):
            AIService(["key"]).answer(request)
    constructor.assert_not_called()

    content = AIService._contents(request)[-1]
    assert content.parts[0].text.endswith("Giải bài trong ảnh")
    assert content.parts[1].inline_data.data == payload
    assert content.parts[1].inline_data.mime_type == "image/png"


def test_image_request_does_not_auto_retry_or_fall_back():
    client = MagicMock()
    client.models.generate_content.side_effect = errors.ServerError(503, {"error": {"code": 503}})
    manager = MagicMock()
    manager.__enter__.return_value = client
    request = AIRequest(Feature.STUDY, AIMode.FAST, "Giải ảnh", [], {}, b"image", "image/jpeg")
    user = SimpleNamespace(id="student")
    service = AIService(
        ["key-a", "key-b"],
        fast_models=["primary", "fallback"],
        max_attempts=3,
        retry_delays=(0, 0),
    )
    with patch("google.genai.Client", return_value=manager):
        with pytest.raises(AIUnavailable):
            service.answer(request, user=user)
    assert client.models.generate_content.call_count == 1
    assert client.models.generate_content.call_args.kwargs["model"] == "primary"


def test_provider_failure_exposes_no_provider_details():
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("secret-api-key-and-private-prompt")
    manager = MagicMock()
    manager.__enter__.return_value = client
    request = AIRequest(Feature.WELLBEING, AIMode.FAST, "Mình buồn", [], {})
    with patch("google.genai.Client", return_value=manager):
        with pytest.raises(AIUnavailable) as error:
            AIService(["key"]).answer(request)
    assert "secret" not in str(error.value)


def test_client_setup_failure_is_retryable_and_fast_budget_is_zero():
    request = AIRequest(Feature.STUDY, AIMode.FAST, "Câu hỏi", [], {})
    with patch("google.genai.Client", side_effect=RuntimeError("private-key")):
        with pytest.raises(AIUnavailable):
            AIService(["key"]).answer(request)
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text="OK")
    manager = MagicMock()
    manager.__enter__.return_value = client
    with patch("google.genai.Client", return_value=manager):
        AIService(["key"], fast_models=["gemini-2.5-flash"]).answer(request)
    assert client.models.generate_content.call_args.kwargs["config"].thinking_config.thinking_budget == 0


@pytest.mark.parametrize(
    ("exception", "kind"),
    [
        (httpx.ConnectError("blocked"), AIErrorKind.NETWORK),
        (httpx.ReadTimeout("slow"), AIErrorKind.TIMEOUT),
        (errors.ClientError(401, {"error": {"code": 401}}), AIErrorKind.AUTHENTICATION),
        (errors.ClientError(403, {"error": {"code": 403}}), AIErrorKind.AUTHENTICATION),
        (errors.ClientError(404, {"error": {"code": 404}}), AIErrorKind.MODEL_NOT_FOUND),
        (errors.ClientError(429, {"error": {"code": 429}}), AIErrorKind.QUOTA),
        (errors.ServerError(503, {"error": {"code": 503}}), AIErrorKind.PROVIDER_UNAVAILABLE),
    ],
)
def test_provider_errors_are_classified_without_sensitive_details(exception, kind):
    error = classify_exception(exception)
    assert error.kind == kind
    assert "blocked" not in str(error) and "slow" not in str(error)


def test_transient_failure_retries_and_falls_back_without_duplicate_keys():
    client = MagicMock()
    client.models.generate_content.side_effect = [
        errors.ServerError(503, {"error": {"code": 503}}),
        SimpleNamespace(text="Fallback OK"),
    ]
    manager = MagicMock()
    manager.__enter__.return_value = client
    request = AIRequest(Feature.STUDY, AIMode.FAST, "Câu hỏi", [], {})
    service = AIService(["same", "same"], fast_models=["primary", "fallback"], retry_delays=(0, 0))
    with patch("google.genai.Client", return_value=manager) as constructor:
        assert service.answer(request) == "Fallback OK"
    assert service.api_keys == ["same"]
    assert constructor.call_count == 2
    assert [call.kwargs["model"] for call in client.models.generate_content.call_args_list] == ["primary", "fallback"]


def test_authentication_error_is_not_retried():
    client = MagicMock()
    client.models.generate_content.side_effect = errors.ClientError(401, {"error": {"code": 401}})
    manager = MagicMock()
    manager.__enter__.return_value = client
    request = AIRequest(Feature.STUDY, AIMode.FAST, "Câu hỏi", [], {})
    with patch("google.genai.Client", return_value=manager):
        with pytest.raises(AIUnavailable) as caught:
            AIService(["key"], fast_models=["model"], retry_delays=(0, 0)).answer(request)
    assert caught.value.kind == AIErrorKind.AUTHENTICATION
    assert client.models.generate_content.call_count == 1


def test_health_check_reports_network_and_success():
    request_client = MagicMock()
    manager = MagicMock()
    manager.__enter__.return_value = request_client
    with patch("google.genai.Client", return_value=manager):
        health = AIService(["key"], fast_models=["model"]).check_connection()
    assert health.ready and health.kind is None
    with patch("google.genai.Client", side_effect=httpx.ConnectError("private detail")):
        health = AIService(["key"], fast_models=["model"]).check_connection()
    assert not health.ready and health.kind == AIErrorKind.NETWORK
    assert "private detail" not in health.message


def test_safety_and_age_appropriate_career_prompts():
    assert "người lớn" in safety_response("Mình không muốn sống nữa")
    assert safety_response("Mình lo về kỳ thi") is None
    request = AIRequest(Feature.CAREER, AIMode.FAST, "hello", [], {"grade": 7})
    prompt = system_instruction(request)
    assert "lớp 11" not in prompt and "Không giới hạn vào nghề công nghệ" in prompt
    assert "mức lương" in prompt
    study_prompt = system_instruction(AIRequest(Feature.STUDY, AIMode.FAST, "Giải bài", [], {"grade": 9}))
    today = datetime.now(LOCAL_TZ).date()
    academic_start = today.year if today.month >= 9 else today.year - 1
    assert f"{academic_start}–{academic_start + 1}" in study_prompt
    assert "không bịa số hiệu văn bản" in study_prompt
    assert "các đoạn có dòng trống" in study_prompt
    image_prompt = system_instruction(
        AIRequest(Feature.STUDY, AIMode.FAST, "Giải ảnh", [], {}, b"image", "image/png")
    )
    assert "dữ kiện bị mờ" in image_prompt


def test_catalog_and_timezone_groups():
    for grade in range(6, 13):
        for subject in subjects(grade):
            if subject != MANUAL:
                assert topics(grade, subject)
    assert "Khoa học tự nhiên" in subjects(9)
    assert "Vật lí" in subjects(10)
    # UTC late evening is already tomorrow in Vietnam.
    assert history_group("2026-10-29T19:00:00+00:00", date(2026, 10, 30)) == "Hôm nay"
    assert history_group("2026-10-28T19:00:00+00:00", date(2026, 10, 30)) == "Hôm qua"
    assert history_group("unknown") == "Cũ hơn"
