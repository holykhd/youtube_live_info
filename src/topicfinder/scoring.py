import math
from datetime import datetime, timedelta


def compute_activity(msg_count: int, cur_keywords: dict[str, int],
                     prev_keywords: dict[str, int]) -> float:
    """버킷 활성도 = 메시지량 가중 × (1 + 신규 키워드 급증률)."""
    if msg_count <= 0:
        return 0.0
    cur_total = sum(cur_keywords.values()) or 1
    prev_set = set(prev_keywords)
    new_weight = sum(c for k, c in cur_keywords.items() if k not in prev_set)
    spike_ratio = new_weight / cur_total          # 0..1
    return math.log(msg_count + 1) * (1.0 + 2.0 * spike_ratio)


def hot_score(channel_count: int, activity_sum: float) -> float:
    """교차 채널 수를 제곱으로 강하게 가중."""
    return (channel_count ** 2) * math.log(activity_sum + 1.0)


def to_absolute_time(started_at_iso: str, t_sec: float) -> str:
    base = datetime.fromisoformat(started_at_iso)
    return (base + timedelta(seconds=t_sec)).isoformat()


def jump_url(video_id: str, t_sec: float) -> str:
    return f"https://www.youtube.com/watch?v={video_id}&t={int(t_sec)}s"
