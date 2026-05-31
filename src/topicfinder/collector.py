import json
import os
import glob
import tempfile
import subprocess
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


def parse_live_chat_lines(lines: list[str], video_id: str) -> list["ChatMsg"]:
    """yt-dlp live_chat.json 라인들을 ChatMsg로 파싱. t_sec = videoOffsetTimeMsec/1000 (원값 유지)."""
    from topicfinder.models import ChatMsg
    out: list[ChatMsg] = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        off = o.get("videoOffsetTimeMsec")
        if off is None:
            continue
        action = o.get("replayChatItemAction") or {}
        for a in action.get("actions", []):
            r = a.get("addChatItemAction", {}).get("item", {}).get("liveChatTextMessageRenderer")
            if not r:
                continue
            text = "".join(x.get("text", "") for x in r.get("message", {}).get("runs", []))
            if not text:
                continue
            author = r.get("authorName", {}).get("simpleText", "")
            out.append(ChatMsg(video_id, int(off) / 1000.0, author, text))
    return out


def _default_fetch_lines(video_id: str, *, timeout_sec: int = 45) -> list[str]:
    """yt-dlp로 live_chat을 임시파일에 받아 라인들 반환. 라이브는 timeout으로 끊고 .part를 파싱."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    tmpdir = tempfile.mkdtemp(prefix="tf_chat_")
    out_tmpl = os.path.join(tmpdir, "chat.%(ext)s")
    cmd = ["yt-dlp", "--skip-download", "--write-subs",
           "--sub-langs", "live_chat", "-o", out_tmpl, url]
    # 라이브는 채팅이 끝나지 않으므로 timeout 후 SIGTERM(graceful)으로 종료시켜
    # yt-dlp가 .part 파일을 디스크에 flush 하도록 한다. SIGKILL은 flush를 막는다.
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        proc.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    files = sorted(glob.glob(os.path.join(tmpdir, "chat.live_chat.json*")))
    lines: list[str] = []
    if files:
        try:
            with open(files[0], encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError:
            lines = []
    for fp in glob.glob(os.path.join(tmpdir, "*")):
        try:
            os.remove(fp)
        except OSError:
            pass
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass
    return lines


def collect_chats(video_id: str, since_t: float, *,
                  fetch_lines=_default_fetch_lines) -> list:
    """since_t 이후의 채팅만 ChatMsg로 변환(증분). 채팅 소스는 yt-dlp live_chat."""
    lines = fetch_lines(video_id)
    msgs = parse_live_chat_lines(lines, video_id)
    return [m for m in msgs if m.t_sec > since_t]
