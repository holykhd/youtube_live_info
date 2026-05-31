from dataclasses import dataclass, field


@dataclass
class ChannelRef:
    url: str
    channel_id: str | None = None
    title: str | None = None


@dataclass
class VideoRef:
    video_id: str
    title: str
    status: str              # 'LIVE' | 'VOD'
    started_at: str          # ISO8601 (KST)
    channel_url: str


@dataclass
class ChatMsg:
    video_id: str
    t_sec: float
    author: str
    message: str


@dataclass
class Bucket:
    video_id: str
    bucket_start: float
    keywords: list[str]
    activity: float
    topic_id: int | None = None


@dataclass
class TopicMatch:
    video_id: str
    start_t_sec: float
    start_abs: str
    jump_url: str


@dataclass
class Topic:
    label: str
    hot_score: float
    channel_count: int
    members: list[TopicMatch] = field(default_factory=list)
