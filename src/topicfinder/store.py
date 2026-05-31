import sqlite3
from topicfinder.models import ChannelRef, VideoRef, ChatMsg, Topic, TopicMatch

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
  id INTEGER PRIMARY KEY, url TEXT UNIQUE, channel_id TEXT, title TEXT,
  enabled INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY, video_id TEXT UNIQUE, channel_url TEXT,
  title TEXT, status TEXT, started_at TEXT, last_chat_t REAL DEFAULT 0,
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS chats (
  id INTEGER PRIMARY KEY, video_id TEXT, t_sec REAL, author TEXT, message TEXT,
  UNIQUE(video_id, t_sec, message)
);
CREATE TABLE IF NOT EXISTS topics (
  id INTEGER PRIMARY KEY, label TEXT, hot_score REAL,
  channel_count INTEGER, first_seen_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS topic_matches (
  id INTEGER PRIMARY KEY, topic_id INTEGER, video_id TEXT,
  start_t_sec REAL, start_abs TEXT, jump_url TEXT,
  UNIQUE(topic_id, video_id)
);
"""


class Store:
    def __init__(self, db_path: str = ":memory:"):
        # check_same_thread=False: 분석 루프 스레드와 웹 요청 스레드가 연결 공유
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # --- channels ---
    def upsert_channel(self, url: str, channel_id: str | None = None,
                       title: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO channels(url, channel_id, title) VALUES(?,?,?) "
            "ON CONFLICT(url) DO UPDATE SET channel_id=excluded.channel_id, "
            "title=excluded.title",
            (url, channel_id, title),
        )
        self.conn.commit()

    def list_channels(self) -> list[ChannelRef]:
        rows = self.conn.execute(
            "SELECT url, channel_id, title FROM channels WHERE enabled=1"
        ).fetchall()
        return [ChannelRef(r["url"], r["channel_id"], r["title"]) for r in rows]

    # --- videos / cursor ---
    def upsert_video(self, v: VideoRef) -> None:
        self.conn.execute(
            "INSERT INTO videos(video_id, channel_url, title, status, started_at) "
            "VALUES(?,?,?,?,?) ON CONFLICT(video_id) DO UPDATE SET "
            "title=excluded.title, status=excluded.status, "
            "started_at=excluded.started_at, updated_at=datetime('now')",
            (v.video_id, v.channel_url, v.title, v.status, v.started_at),
        )
        self.conn.commit()

    def get_last_chat_t(self, video_id: str) -> float:
        row = self.conn.execute(
            "SELECT last_chat_t FROM videos WHERE video_id=?", (video_id,)
        ).fetchone()
        return row["last_chat_t"] if row else 0.0

    def set_last_chat_t(self, video_id: str, t: float) -> None:
        self.conn.execute(
            "UPDATE videos SET last_chat_t=? WHERE video_id=?", (t, video_id)
        )
        self.conn.commit()

    # --- chats ---
    def insert_chats(self, msgs: list[ChatMsg]) -> int:
        before = self.conn.total_changes
        self.conn.executemany(
            "INSERT OR IGNORE INTO chats(video_id, t_sec, author, message) "
            "VALUES(?,?,?,?)",
            [(m.video_id, m.t_sec, m.author, m.message) for m in msgs],
        )
        self.conn.commit()
        return self.conn.total_changes - before

    def get_chats_since(self, video_id: str, t: float) -> list[ChatMsg]:
        rows = self.conn.execute(
            "SELECT video_id, t_sec, author, message FROM chats "
            "WHERE video_id=? AND t_sec>? ORDER BY t_sec", (video_id, t)
        ).fetchall()
        return [ChatMsg(r["video_id"], r["t_sec"], r["author"], r["message"])
                for r in rows]

    # --- topics / matches (사이클 스냅샷) ---
    def save_topics(self, topics: list[Topic]) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM topic_matches")
        cur.execute("DELETE FROM topics")
        for t in topics:
            cur.execute(
                "INSERT INTO topics(label, hot_score, channel_count) VALUES(?,?,?)",
                (t.label, t.hot_score, t.channel_count),
            )
            tid = cur.lastrowid
            for m in t.members:
                cur.execute(
                    "INSERT OR IGNORE INTO topic_matches"
                    "(topic_id, video_id, start_t_sec, start_abs, jump_url) "
                    "VALUES(?,?,?,?,?)",
                    (tid, m.video_id, m.start_t_sec, m.start_abs, m.jump_url),
                )
        self.conn.commit()

    def load_topics(self) -> list[Topic]:
        trows = self.conn.execute(
            "SELECT id, label, hot_score, channel_count FROM topics "
            "ORDER BY hot_score DESC"
        ).fetchall()
        topics = []
        for tr in trows:
            mrows = self.conn.execute(
                "SELECT video_id, start_t_sec, start_abs, jump_url "
                "FROM topic_matches WHERE topic_id=? ORDER BY start_abs",
                (tr["id"],),
            ).fetchall()
            members = [TopicMatch(m["video_id"], m["start_t_sec"],
                                  m["start_abs"], m["jump_url"]) for m in mrows]
            topics.append(Topic(tr["label"], tr["hot_score"],
                                tr["channel_count"], members))
        return topics

    def current_labels(self) -> list[str]:
        rows = self.conn.execute("SELECT label FROM topics").fetchall()
        return [r["label"] for r in rows]
