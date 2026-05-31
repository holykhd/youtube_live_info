import json
from pathlib import Path
from topicfinder.models import Bucket
from topicfinder.llm import build_prompt, parse_response, judge_topics

FIXTURE = Path(__file__).parent / "fixtures" / "llm_response.json"


def test_build_prompt_includes_keywords_and_prev_labels():
    buckets = [Bucket("v1", 0.0, ["금리", "연준"], 5.0)]
    prompt = build_prompt(buckets, prev_labels=["환율 급등"])
    assert "금리" in prompt and "연준" in prompt
    assert "v1" in prompt
    assert "환율 급등" in prompt


def test_parse_response_extracts_topics():
    raw = FIXTURE.read_text(encoding="utf-8")
    topics = parse_response(raw)
    assert topics[0]["label"] == "연준 금리/파월 발언"
    assert len(topics[0]["members"]) == 2


def test_parse_response_handles_codefence():
    raw = "```json\n" + FIXTURE.read_text(encoding="utf-8") + "\n```"
    topics = parse_response(raw)
    assert topics[0]["label"] == "연준 금리/파월 발언"


def test_judge_topics_uses_injected_runner():
    buckets = [Bucket("v1", 0.0, ["금리"], 5.0)]
    fake_output = FIXTURE.read_text(encoding="utf-8")
    captured = {}

    def fake_runner(prompt: str, model: str) -> str:
        captured["prompt"] = prompt
        captured["model"] = model
        return fake_output

    topics = judge_topics(buckets, prev_labels=[], runner=fake_runner, model="haiku")
    assert captured["model"] == "haiku"
    assert topics[0]["label"] == "연준 금리/파월 발언"
