from topicfinder.models import ChatMsg

# 0~120초 버킷: 금리/연준 관련 의미 채팅이 몰림
# 120~240초 버킷: 잡담·이모지뿐
SAMPLE = [
    ChatMsg("v1", 5.0, "u1", "연준 금리 인상하나요"),
    ChatMsg("v1", 12.0, "u2", "파월 발언 시작됐다"),
    ChatMsg("v1", 33.0, "u3", "금리 동결 예상이요"),
    ChatMsg("v1", 80.0, "u4", "연준 매파적이네"),
    ChatMsg("v1", 119.0, "u5", "금리 금리 금리"),
    ChatMsg("v1", 130.0, "u6", "ㅋㅋㅋㅋ"),
    ChatMsg("v1", 145.0, "u7", "안녕하세요"),
    ChatMsg("v1", 200.0, "u8", "ㅎㅇ"),
]
