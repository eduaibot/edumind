from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import uuid4

LOCAL_TZ = timezone(timedelta(hours=7))


class Feature(str, Enum):
    STUDY = "study"
    WELLBEING = "wellbeing"
    CAREER = "career"


class AIMode(str, Enum):
    FAST = "fast"
    THINKING = "thinking"


FEATURE_LABELS = {
    Feature.STUDY: "Học tập & ôn thi",
    Feature.WELLBEING: "Chăm sóc tinh thần",
    Feature.CAREER: "Định hướng tương lai",
}
MODE_LABELS = {AIMode.FAST: "Nhanh", AIMode.THINKING: "Tư duy"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def history_group(timestamp, today=None):
    if not timestamp:
        return "Cũ hơn"
    try:
        value = datetime.fromisoformat(timestamp)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        days = ((today or datetime.now(LOCAL_TZ).date()) - value.astimezone(LOCAL_TZ).date()).days
    except (ValueError, TypeError):
        return "Cũ hơn"
    if days <= 0:
        return "Hôm nay"
    if days == 1:
        return "Hôm qua"
    if days < 7:
        return "7 ngày qua"
    if days < 30:
        return "30 ngày qua"
    return "Cũ hơn"


@dataclass
class Conversation:
    feature: Feature
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = "Cuộc trò chuyện mới"
    messages: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: str | None = field(default_factory=now_iso)
    updated_at: str | None = field(default_factory=now_iso)
    owner: str | None = None
    persisted: bool = False
    save_enabled: bool = False

    def add_question(self, text):
        if not self.messages:
            self.title = " ".join(text.split())[:80] or "Cuộc trò chuyện mới"
        self.messages.append({"role": "user", "content": text})
        self.updated_at = now_iso()


@dataclass(frozen=True)
class AIRequest:
    feature: Feature
    mode: AIMode
    text: str
    history: list[dict]
    context: dict
