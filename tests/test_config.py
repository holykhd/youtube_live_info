from topicfinder.config import Config


def test_default_config_values():
    cfg = Config()
    assert cfg.cycle_interval_sec == 1200          # 20분 절약 주기
    assert cfg.bucket_size_sec == 120              # 2분 버킷
    assert cfg.activity_threshold == 3.0
    assert cfg.min_keywords == 2
    assert cfg.max_llm_calls_per_cycle == 2
    assert cfg.llm_model == "haiku"
    assert cfg.top_keywords_per_bucket == 8
    assert cfg.max_msgs_per_bucket == 500
    assert cfg.db_path == "data/topicfinder.db"


def test_ensure_dirs_creates_parent(tmp_path):
    db = tmp_path / "nested" / "topicfinder.db"
    cfg = Config(db_path=str(db))
    cfg.ensure_dirs()
    assert db.parent.is_dir()


def test_config_override():
    cfg = Config(cycle_interval_sec=300, llm_model="sonnet")
    assert cfg.cycle_interval_sec == 300
    assert cfg.llm_model == "sonnet"
