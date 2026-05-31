from datetime import datetime, timezone, timedelta
from topicfinder.models import VideoRef

KST = timezone(timedelta(hours=9))


def _ts_to_kst_iso(ts: int | None) -> str:
    if not ts:
        return datetime.now(KST).isoformat()
    return datetime.fromtimestamp(ts, KST).isoformat()


def _default_extract(url: str) -> dict:
    import yt_dlp
    opts = {"quiet": True, "skip_download": True, "extract_flat": "in_playlist"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def identify_video(channel_url: str, *, extract=_default_extract) -> VideoRef | None:
    """진행 중 라이브가 있으면 그것을, 없으면 마지막 라이브(VOD)를 식별."""
    base = channel_url.rstrip("/")
    # 1) 진행 중 라이브 시도
    try:
        info = extract(base + "/live")
        if info and info.get("is_live"):
            return VideoRef(info["id"], info.get("title", ""), "LIVE",
                            _ts_to_kst_iso(info.get("timestamp")), channel_url)
    except Exception:
        pass
    # 2) 마지막 라이브(VOD) 폴백
    try:
        streams = extract(base + "/streams")
    except Exception:
        return None
    entries = (streams or {}).get("entries") or []
    if not entries:
        return None
    e = entries[0]
    return VideoRef(e["id"], e.get("title", ""), "VOD",
                    _ts_to_kst_iso(e.get("timestamp")), channel_url)


def _default_get_chat(video_id: str) -> list[dict]:
    from chat_downloader import ChatDownloader
    url = f"https://www.youtube.com/watch?v={video_id}"
    return list(ChatDownloader().get_chat(url))


def collect_chats(video_id: str, since_t: float, *,
                  get_chat=_default_get_chat) -> list:
    """since_t 이후의 채팅만 ChatMsg 로 변환(증분)."""
    from topicfinder.models import ChatMsg
    out = []
    for m in get_chat(video_id):
        t = float(m.get("time_in_seconds") or 0.0)
        if t <= since_t:
            continue
        author = (m.get("author") or {}).get("name", "")
        out.append(ChatMsg(video_id, t, author, m.get("message", "")))
    return out
