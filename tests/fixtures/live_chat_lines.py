# yt-dlp live_chat.json 형식의 샘플 라인들 (실제 구조 기반)
def _line(offset_ms, author, text):
    import json
    return json.dumps({
        "replayChatItemAction": {"actions": [
            {"addChatItemAction": {"item": {"liveChatTextMessageRenderer": {
                "message": {"runs": [{"text": text}]},
                "authorName": {"simpleText": author},
            }}}}
        ]},
        "videoOffsetTimeMsec": str(offset_ms),
        "isLive": True,
    }, ensure_ascii=False)


SAMPLE_LINES = [
    _line(0, "u1", "연준 금리 인상"),
    _line(5000, "u2", "파월 발언 시작"),
    _line(130000, "u3", "ㅋㅋㅋㅋ"),
    "not json at all",                         # 비JSON → skip
    '{"videoOffsetTimeMsec":"7000"}',          # 메시지 없음 → skip
    '{"replayChatItemAction":{"actions":[]}}', # offset 없음 → skip
]
