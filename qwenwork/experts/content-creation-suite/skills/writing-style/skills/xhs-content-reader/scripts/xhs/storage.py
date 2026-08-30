"""SQLite 持久化存储 — 帖子与评论。

存储路径:  ~/.dingclaw/xhs/data/xhs.db
身份文件:  ~/.dingclaw/xhs/data/me.json（各账号的 author_id，用于 is_mine 标记）

业务表（2张）:
  notes    — 帖子（Feed 列表轻量数据 + FeedDetail 完整数据）
  comments — 评论与回复（递归平铺，parent_id 区分层级）
"""

from __future__ import annotations

import contextlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xhs.types import Comment, Feed, FeedDetail


# ========== 工具函数 ==========


def _parse_count(s: str) -> int:
    """解析互动数量字符串为整数。

    支持: "1234", "1.2万", "3.5千", "999+", "" → 0
    """
    if not s:
        return 0
    s = s.strip()
    try:
        m = re.match(r"^([\d.]+)万$", s)
        if m:
            return int(float(m.group(1)) * 10000)
        m = re.match(r"^([\d.]+)千$", s)
        if m:
            return int(float(m.group(1)) * 1000)
        # 纯数字或 "999+" 取开头数字部分
        m = re.match(r"^(\d+)", s)
        if m:
            return int(m.group(1))
        return 0
    except (ValueError, TypeError):
        return 0


def _now_iso() -> str:
    """返回当前 UTC 时间 ISO8601 字符串（如 2026-03-10T08:00:00Z）。"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ========== 主类 ==========


class XHSStorage:
    """小红书数据 SQLite 存储。

    多账号通过 account 参数隔离：写入时注入，查询时按 account 过滤。

    使用方式:
        storage = XHSStorage(account="default")
        storage.upsert_notes_from_feeds(feeds, keyword="护肤")
        notes = storage.query_notes(keyword="护肤", limit=10)
        storage.close()
    """

    DEFAULT_DB_PATH = Path.home() / ".dingclaw" / "xhs" / "data" / "xhs.db"

    def __init__(self, db_path: Path | None = None, account: str = "default") -> None:
        self._db_path = db_path or self.DEFAULT_DB_PATH
        self._account = account or "default"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()

    def close(self) -> None:
        """关闭数据库连接。"""
        self._conn.close()

    # ========== 内部：建表 ==========

    def _init_db(self) -> None:
        """建表，幂等（CREATE TABLE/INDEX IF NOT EXISTS）。"""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                note_id       TEXT PRIMARY KEY,
                xsec_token    TEXT,
                title         TEXT,
                desc          TEXT,
                note_type     TEXT,
                author_id     TEXT,
                author_name   TEXT,
                like_count    INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                collect_count INTEGER DEFAULT 0,
                share_count   INTEGER DEFAULT 0,
                published_at  INTEGER,
                ip_location   TEXT,
                is_mine       INTEGER DEFAULT 0,
                keywords      TEXT,
                raw_json      TEXT,
                account       TEXT DEFAULT 'default',
                collected_at  TEXT,
                updated_at    TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_notes_account    ON notes(account);
            CREATE INDEX IF NOT EXISTS idx_notes_is_mine    ON notes(is_mine);
            CREATE INDEX IF NOT EXISTS idx_notes_author_id  ON notes(author_id);
            CREATE INDEX IF NOT EXISTS idx_notes_collected  ON notes(collected_at);

            CREATE TABLE IF NOT EXISTS comments (
                comment_id   TEXT PRIMARY KEY,
                note_id      TEXT,
                parent_id    TEXT,
                content      TEXT,
                author_id    TEXT,
                author_name  TEXT,
                is_mine      INTEGER DEFAULT 0,
                like_count   INTEGER DEFAULT 0,
                ip_location  TEXT,
                published_at INTEGER,
                account      TEXT DEFAULT 'default',
                collected_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_comments_note    ON comments(note_id);
            CREATE INDEX IF NOT EXISTS idx_comments_is_mine ON comments(is_mine);
            CREATE INDEX IF NOT EXISTS idx_comments_author  ON comments(author_id);
            CREATE INDEX IF NOT EXISTS idx_comments_pub     ON comments(published_at);

            CREATE TABLE IF NOT EXISTS users (
                user_id        TEXT PRIMARY KEY,
                nickname       TEXT,
                avatar         TEXT,
                gender         INTEGER,
                ip_location    TEXT,
                desc           TEXT,
                red_id         TEXT,
                follows_count  INTEGER DEFAULT 0,
                fans_count     INTEGER DEFAULT 0,
                likes_count    INTEGER DEFAULT 0,
                notes_count    INTEGER DEFAULT 0,
                is_potential   INTEGER DEFAULT 0,
                intent_type    TEXT,
                last_seen_at   INTEGER,
                account        TEXT DEFAULT 'default',
                collected_at   TEXT,
                updated_at     TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_users_account  ON users(account);
            CREATE INDEX IF NOT EXISTS idx_users_intent   ON users(intent_type);
            CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen_at);
        """)
        self._migrate_comments_schema()
        self._conn.commit()

    def _migrate_comments_schema(self) -> None:
        """为 comments 表添加 sub_comment_count、sub_comment_ids、replied_by_me 列（若不存在）。"""
        cur = self._conn.execute("PRAGMA table_info(comments)")
        cols = {row[1] for row in cur.fetchall()}
        added = False
        for col, sql_type in [
            ("sub_comment_count", "INTEGER DEFAULT 0"),
            ("sub_comment_ids", "TEXT"),
            ("replied_by_me", "INTEGER DEFAULT 0"),
        ]:
            if col not in cols:
                self._conn.execute(f"ALTER TABLE comments ADD COLUMN {col} {sql_type}")
                added = True
        if added:
            self._migrate_comments_aggregates()

    def _migrate_comments_aggregates(self) -> None:
        """对已有顶层评论，根据回复行计算并更新 sub_comment_count、sub_comment_ids、replied_by_me。"""
        my_id = self.get_my_author_id()
        rows = self._conn.execute(
            """
            SELECT p.comment_id,
                   COUNT(c.comment_id) AS cnt,
                   GROUP_CONCAT(c.comment_id) AS ids,
                   MAX(CASE WHEN c.author_id=? THEN 1 ELSE 0 END) AS replied
            FROM comments p
            LEFT JOIN comments c ON c.parent_id=p.comment_id AND c.account=p.account
            WHERE p.parent_id IS NULL AND p.account=?
            GROUP BY p.comment_id
            """,
            (my_id, self._account),
        ).fetchall()
        for r in rows:
            ids_str = r["ids"] or ""
            ids_list = [x.strip() for x in ids_str.split(",")] if ids_str else []
            sub_ids = json.dumps(ids_list, ensure_ascii=False) if ids_list else "[]"
            self._conn.execute(
                "UPDATE comments SET sub_comment_count=?, sub_comment_ids=?, replied_by_me=? "
                "WHERE comment_id=? AND account=?",
                (r["cnt"], sub_ids, r["replied"] or 0, r["comment_id"], self._account),
            )

    # ========== 内部：身份文件（me.json sidecar）==========

    def _me_file(self) -> Path:
        return self._db_path.parent / "me.json"

    def set_my_identity(self, author_id: str) -> None:
        """保存当前账号的 author_id，供后续评论 is_mine 标记使用。"""
        if not author_id:
            return
        me_file = self._me_file()
        data: dict = {}
        if me_file.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                data = json.loads(me_file.read_text(encoding="utf-8"))
        data[self._account] = author_id
        me_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_my_author_id(self) -> str:
        """读取当前账号的 author_id（未知则返回空字符串）。"""
        me_file = self._me_file()
        if not me_file.exists():
            return ""
        try:
            data = json.loads(me_file.read_text(encoding="utf-8"))
            return data.get(self._account, "")
        except (json.JSONDecodeError, OSError):
            return ""

    # ========== 内部：工具方法 ==========

    @staticmethod
    def _merge_keyword(existing_json: str | None, keyword: str | None) -> str:
        """将新关键词合并进现有 JSON 数组（去重）。"""
        kws: list[str] = json.loads(existing_json or "[]")
        if keyword and keyword not in kws:
            kws.append(keyword)
        return json.dumps(kws, ensure_ascii=False)

    def _read_keywords(self, note_id: str) -> str:
        """读取已存储的 keywords JSON 字符串。"""
        row = self._conn.execute(
            "SELECT keywords FROM notes WHERE note_id=?", (note_id,)
        ).fetchone()
        return row["keywords"] if row else "[]"

    def _flatten_comments(
        self,
        comments: list[Comment],
        note_id: str,
        my_author_id: str = "",
        parent_id: str | None = None,
    ) -> list[tuple]:
        """递归平铺评论树，返回可直接 executemany 的行元组列表。"""
        now = _now_iso()
        rows = []
        for c in comments:
            is_mine = 1 if (my_author_id and c.user_info.user_id == my_author_id) else 0
            if parent_id is None:
                sub_count = len(c.sub_comments)
                sub_ids = json.dumps([sc.id for sc in c.sub_comments], ensure_ascii=False)
                replied = 1 if any(
                    sc.user_info.user_id == my_author_id for sc in c.sub_comments
                ) and my_author_id else 0
            else:
                sub_count = 0
                sub_ids = "[]"
                replied = 0
            rows.append((
                c.id,
                note_id,
                parent_id,
                c.content,
                c.user_info.user_id,
                c.user_info.nickname or c.user_info.nick_name,
                is_mine,
                _parse_count(c.like_count),
                c.ip_location,
                c.create_time or None,
                self._account,
                now,
                sub_count,
                sub_ids,
                replied,
            ))
            if c.sub_comments:
                rows.extend(
                    self._flatten_comments(c.sub_comments, note_id, my_author_id, parent_id=c.id)
                )
        return rows

    # ========== 写入 ==========

    def upsert_note(
        self,
        detail: FeedDetail,
        *,
        is_mine: bool = False,
        keywords: list[str] | None = None,
    ) -> None:
        """从 FeedDetail 写入帖子完整数据。已有数据则更新（含 raw_json）。"""
        now = _now_iso()
        raw = json.dumps(detail.to_dict(), ensure_ascii=False)
        # 合并关键词：保留已有的，再追加新的
        merged_kw = self._read_keywords(detail.note_id)
        for kw in keywords or []:
            merged_kw = self._merge_keyword(merged_kw, kw)

        self._conn.execute(
            """
            INSERT INTO notes (
                note_id, xsec_token, title, desc, note_type,
                author_id, author_name,
                like_count, comment_count, collect_count, share_count,
                published_at, ip_location, is_mine, keywords,
                raw_json, account, collected_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(note_id) DO UPDATE SET
                title         = excluded.title,
                desc          = excluded.desc,
                like_count    = excluded.like_count,
                comment_count = excluded.comment_count,
                collect_count = excluded.collect_count,
                share_count   = excluded.share_count,
                published_at  = excluded.published_at,
                ip_location   = excluded.ip_location,
                is_mine       = MAX(is_mine, excluded.is_mine),
                keywords      = excluded.keywords,
                raw_json      = excluded.raw_json,
                updated_at    = excluded.updated_at
            """,
            (
                detail.note_id,
                detail.xsec_token,
                detail.title,
                detail.desc,
                detail.type,
                detail.user.user_id,
                detail.user.nickname or detail.user.nick_name,
                _parse_count(detail.interact_info.liked_count),
                _parse_count(detail.interact_info.comment_count),
                _parse_count(detail.interact_info.collected_count),
                _parse_count(detail.interact_info.shared_count),
                detail.time or None,
                detail.ip_location,
                1 if is_mine else 0,
                merged_kw,
                raw,
                self._account,
                now,
                now,
            ),
        )
        self._conn.commit()

    def upsert_notes_from_feeds(
        self,
        feeds: list[Feed],
        *,
        keyword: str | None = None,
    ) -> None:
        """从 Feed 列表写入轻量帖子数据。

        - 首次写入时插入基础字段（title/type/author 等）。
        - 再次写入时只更新互动计数和关键词，不影响 title/raw_json 等详情字段。
        """
        now = _now_iso()
        for feed in feeds:
            if not feed.id:
                continue
            card = feed.note_card
            user = card.user
            info = card.interact_info
            merged_kw = self._merge_keyword(self._read_keywords(feed.id), keyword)

            self._conn.execute(
                """
                INSERT INTO notes (
                    note_id, xsec_token, title, note_type,
                    author_id, author_name,
                    like_count, comment_count, collect_count, share_count,
                    is_mine, keywords, account, collected_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                ON CONFLICT(note_id) DO UPDATE SET
                    xsec_token    = excluded.xsec_token,
                    title       = CASE WHEN raw_json IS NULL
                                    THEN excluded.title ELSE title END,
                    note_type   = CASE WHEN raw_json IS NULL
                                    THEN excluded.note_type ELSE note_type END,
                    author_name = CASE WHEN raw_json IS NULL
                                    THEN excluded.author_name ELSE author_name END,
                    like_count    = excluded.like_count,
                    comment_count = excluded.comment_count,
                    collect_count = excluded.collect_count,
                    share_count   = excluded.share_count,
                    keywords      = excluded.keywords,
                    updated_at    = excluded.updated_at
                """,
                (
                    feed.id,
                    feed.xsec_token,
                    card.display_title,
                    card.type,
                    user.user_id,
                    user.nickname or user.nick_name,
                    _parse_count(info.liked_count),
                    _parse_count(info.comment_count),
                    _parse_count(info.collected_count),
                    _parse_count(info.shared_count),
                    merged_kw,
                    self._account,
                    now,
                    now,
                ),
            )
        self._conn.commit()

    def upsert_comments(
        self,
        comments: list[Comment],
        note_id: str,
        *,
        my_author_id: str | None = None,
    ) -> None:
        """写入评论列表（递归平铺 sub_comments）。

        is_mine 通过 my_author_id 或 me.json 中已存储的身份自动判断。
        """
        known_my_id = my_author_id or self.get_my_author_id()
        rows = self._flatten_comments(comments, note_id, known_my_id)
        self._conn.executemany(
            """
            INSERT INTO comments (
                comment_id, note_id, parent_id, content,
                author_id, author_name, is_mine, like_count,
                ip_location, published_at, account, collected_at,
                sub_comment_count, sub_comment_ids, replied_by_me
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(comment_id) DO UPDATE SET
                content           = excluded.content,
                like_count        = excluded.like_count,
                is_mine           = MAX(is_mine, excluded.is_mine),
                collected_at      = excluded.collected_at,
                sub_comment_count = excluded.sub_comment_count,
                sub_comment_ids   = excluded.sub_comment_ids,
                replied_by_me     = MAX(replied_by_me, excluded.replied_by_me)
            """,
            rows,
        )
        self._conn.commit()

    def mark_notes_mine(self, note_ids: list[str]) -> None:
        """将指定 note_id 列表标记为 is_mine=1。供 my-profile 命令调用。"""
        if not note_ids:
            return
        placeholders = ",".join("?" * len(note_ids))
        self._conn.execute(
            f"UPDATE notes SET is_mine=1 WHERE note_id IN ({placeholders}) AND account=?",
            [*note_ids, self._account],
        )
        self._conn.commit()

    def mark_comments_mine(self, author_id: str) -> None:
        """将指定 author_id 的全部已存评论标记为 is_mine=1（回溯标记）。"""
        if not author_id:
            return
        self._conn.execute(
            "UPDATE comments SET is_mine=1 WHERE author_id=? AND account=?",
            (author_id, self._account),
        )
        self._conn.commit()

    def add_reply_to_parent(
        self,
        parent_id: str,
        new_comment_id: str,
        note_id: str,
        is_mine: bool = False,
        *,
        content: str = "",
        author_id: str = "",
        author_name: str = "",
    ) -> None:
        """增量更新：在父评论下添加一条回复记录。

        更新父评论的 sub_comment_count、sub_comment_ids、replied_by_me；
        若新回复不存在则 INSERT 占位行。
        """
        now = _now_iso()
        parent = self._conn.execute(
            "SELECT sub_comment_count, sub_comment_ids, replied_by_me FROM comments "
            "WHERE comment_id=? AND account=?",
            (parent_id, self._account),
        ).fetchone()
        if not parent:
            return
        sub_ids: list[str] = json.loads(parent["sub_comment_ids"] or "[]")
        if new_comment_id in sub_ids:
            return
        sub_ids.append(new_comment_id)
        new_count = (parent["sub_comment_count"] or 0) + 1
        new_replied = max(parent["replied_by_me"] or 0, 1 if is_mine else 0)
        self._conn.execute(
            "UPDATE comments SET sub_comment_count=?, sub_comment_ids=?, replied_by_me=? "
            "WHERE comment_id=? AND account=?",
            (new_count, json.dumps(sub_ids, ensure_ascii=False), new_replied, parent_id, self._account),
        )
        published_ms = int(datetime.now(UTC).timestamp() * 1000)
        self._conn.execute(
            """
            INSERT INTO comments (
                comment_id, note_id, parent_id, content,
                author_id, author_name, is_mine, like_count,
                ip_location, published_at, account, collected_at,
                sub_comment_count, sub_comment_ids, replied_by_me
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, '', ?, ?, ?, 0, '[]', 0)
            ON CONFLICT(comment_id) DO NOTHING
            """,
            (
                new_comment_id,
                note_id,
                parent_id,
                content or "",
                author_id or "",
                author_name or "",
                1 if is_mine else 0,
                published_ms,
                self._account,
                now,
            ),
        )
        self._conn.commit()

    # ========== 查询 ==========

    def query_notes(
        self,
        *,
        mine_only: bool = False,
        keyword: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """查询帖子列表。

        keyword 匹配 title、desc 或 keywords 字段（LIKE）。
        结果按 published_at 降序，未知时间的排在最后。
        """
        conditions = ["account = ?"]
        params: list = [self._account]
        if mine_only:
            conditions.append("is_mine = 1")
        if keyword:
            conditions.append("(title LIKE ? OR desc LIKE ? OR keywords LIKE ?)")
            like = f"%{keyword}%"
            params.extend([like, like, like])
        where = " AND ".join(conditions)
        rows = self._conn.execute(
            f"SELECT * FROM notes WHERE {where} "
            "ORDER BY COALESCE(published_at, 0) DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return [dict(r) for r in rows]

    def query_comments(
        self,
        *,
        note_id: str | None = None,
        mine_only: bool = False,
        limit: int = 20,
        offset: int = 0,
        author_id: str | None = None,
        keyword: str | None = None,
    ) -> list[dict]:
        """查询评论列表。

        可按 note_id 过滤（某帖子的评论），可只看我发的（is_mine=1）。
        结果按 published_at 降序。
        """
        conditions = ["account = ?"]
        params: list = [self._account]
        if note_id:
            conditions.append("note_id = ?")
            params.append(note_id)
        if author_id:
            conditions.append("author_id = ?")
            params.append(author_id)
        if keyword:
            conditions.append("content LIKE ?")
            params.append(f"%{keyword}%")
        if mine_only:
            conditions.append("is_mine = 1")
        where = " AND ".join(conditions)
        rows = self._conn.execute(
            f"SELECT * FROM comments WHERE {where} "
            "ORDER BY COALESCE(published_at, 0) DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return [dict(r) for r in rows]

    def query_comment_authors(
        self,
        *,
        note_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """按帖子聚合评论用户，返回用户画像分析常用字段。"""
        rows = self._conn.execute(
            """
            SELECT
                c.author_id,
                c.author_name,
                COUNT(*) AS comment_count,
                MAX(c.published_at) AS last_comment_at,
                COALESCE(MAX(c.like_count), 0) AS max_comment_like,
                u.nickname,
                u.gender,
                u.ip_location,
                u.fans_count,
                u.follows_count,
                u.likes_count,
                u.notes_count,
                u.intent_type,
                u.is_potential
            FROM comments c
            LEFT JOIN users u
                ON u.user_id = c.author_id
               AND u.account = c.account
            WHERE c.account = ?
              AND c.note_id = ?
              AND COALESCE(c.author_id, '') != ''
            GROUP BY c.author_id, c.author_name
            ORDER BY comment_count DESC, COALESCE(last_comment_at, 0) DESC
            LIMIT ?
            """,
            (self._account, note_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_local(
        self,
        query: str,
        *,
        target: str = "notes",
        limit: int = 10,
    ) -> list[dict]:
        """在本地数据库全文 LIKE 检索。

        target: 'notes'（默认，匹配 title/desc）| 'comments'（匹配 content）
        """
        like = f"%{query}%"
        if target == "comments":
            rows = self._conn.execute(
                "SELECT * FROM comments WHERE account=? AND content LIKE ? "
                "ORDER BY COALESCE(published_at, 0) DESC LIMIT ?",
                (self._account, like, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM notes WHERE account=? AND (title LIKE ? OR desc LIKE ?) "
                "ORDER BY COALESCE(published_at, 0) DESC LIMIT ?",
                (self._account, like, like, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def trend_analysis(self, keyword: str, days: int = 30) -> dict:
        """按关键词统计近 N 天帖子互动趋势（按采集日期分组）。

        返回格式:
            {
                "keyword": "护肤",
                "days": 30,
                "data_points": [{"date": "2026-03-01", "note_count": 5, ...}],
                "summary": {"total_notes": 25, "avg_likes": 1234.5, ...}
            }
        """
        cutoff = (datetime.now(UTC) - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        like_kw = f"%{keyword}%"
        base_params = (self._account, like_kw, like_kw, like_kw, cutoff)

        rows = self._conn.execute(
            """
            SELECT
                DATE(collected_at)  AS date,
                COUNT(*)            AS note_count,
                AVG(like_count)     AS avg_likes,
                AVG(comment_count)  AS avg_comments,
                AVG(collect_count)  AS avg_collects
            FROM notes
            WHERE account = ?
              AND (title LIKE ? OR desc LIKE ? OR keywords LIKE ?)
              AND collected_at >= ?
            GROUP BY DATE(collected_at)
            ORDER BY date ASC
            """,
            base_params,
        ).fetchall()

        data_points = [
            {
                "date": r["date"],
                "note_count": r["note_count"],
                "avg_likes": round(r["avg_likes"] or 0, 1),
                "avg_comments": round(r["avg_comments"] or 0, 1),
                "avg_collects": round(r["avg_collects"] or 0, 1),
            }
            for r in rows
        ]

        summary = self._conn.execute(
            """
            SELECT COUNT(*) AS total, AVG(like_count) AS avg_likes,
                   AVG(comment_count) AS avg_comments
            FROM notes
            WHERE account = ?
              AND (title LIKE ? OR desc LIKE ? OR keywords LIKE ?)
              AND collected_at >= ?
            """,
            base_params,
        ).fetchone()

        return {
            "keyword": keyword,
            "days": days,
            "data_points": data_points,
            "summary": {
                "total_notes": summary["total"] if summary else 0,
                "avg_likes": round((summary["avg_likes"] or 0) if summary else 0, 1),
                "avg_comments": round((summary["avg_comments"] or 0) if summary else 0, 1),
            },
        }

    def get_note(self, note_id: str) -> dict | None:
        """按 note_id 查询单条帖子，不存在则返回 None。"""
        row = self._conn.execute(
            "SELECT * FROM notes WHERE note_id=? AND account=?",
            (note_id, self._account),
        ).fetchone()
        return dict(row) if row else None

    # ========== 用户管理 ==========

    def upsert_user(self, user_data: dict) -> None:
        """插入或更新用户信息。

        user_data 应包含:
            - user_id (必填)
            - nickname, avatar, gender, ip_location, desc, red_id
            - follows_count, fans_count, likes_count, notes_count
            - last_seen_at (Unix 毫秒时间戳)
        """
        if not user_data.get("user_id"):
            return

        now = _now_iso()
        self._conn.execute(
            """
            INSERT INTO users (
                user_id, nickname, avatar, gender, ip_location, desc, red_id,
                follows_count, fans_count, likes_count, notes_count,
                is_potential, intent_type, last_seen_at,
                account, collected_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                nickname      = excluded.nickname,
                avatar        = excluded.avatar,
                gender        = excluded.gender,
                ip_location   = excluded.ip_location,
                desc          = excluded.desc,
                red_id        = excluded.red_id,
                follows_count = excluded.follows_count,
                fans_count    = excluded.fans_count,
                likes_count   = excluded.likes_count,
                notes_count   = excluded.notes_count,
                last_seen_at  = excluded.last_seen_at,
                updated_at    = excluded.updated_at
            """,
            (
                user_data["user_id"],
                user_data.get("nickname", ""),
                user_data.get("avatar", ""),
                user_data.get("gender", 0),
                user_data.get("ip_location", ""),
                user_data.get("desc", ""),
                user_data.get("red_id", ""),
                user_data.get("follows_count", 0),
                user_data.get("fans_count", 0),
                user_data.get("likes_count", 0),
                user_data.get("notes_count", 0),
                user_data.get("last_seen_at"),
                self._account,
                now,
                now,
            ),
        )
        self._conn.commit()

    def query_user(self, user_id: str) -> dict | None:
        """查询单个用户信息，不存在则返回 None。"""
        row = self._conn.execute(
            "SELECT * FROM users WHERE user_id=? AND account=?",
            (user_id, self._account),
        ).fetchone()
        return dict(row) if row else None

    def query_users_by_intent(self, intent_type: str, limit: int = 20) -> list[dict]:
        """按意向类型查询用户列表。"""
        rows = self._conn.execute(
            "SELECT * FROM users WHERE account=? AND intent_type=? "
            "ORDER BY last_seen_at DESC LIMIT ?",
            (self._account, intent_type, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def query_users_batch(self, user_ids: list[str]) -> dict[str, dict]:
        """批量查询用户信息，返回 {user_id: user_data} 字典。

        仅返回本地存在的用户，不存在的 user_id 不会出现在结果中。
        """
        if not user_ids:
            return {}

        placeholders = ",".join("?" * len(user_ids))
        rows = self._conn.execute(
            f"SELECT * FROM users WHERE user_id IN ({placeholders}) AND account=?",
            [*user_ids, self._account],
        ).fetchall()

        result = {}
        for row in rows:
            user_dict = dict(row)
            result[user_dict["user_id"]] = user_dict
        return result

    def query_users(
        self,
        *,
        user_id: str | None = None,
        intent_type: str | None = None,
        keyword: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """按维度查询用户列表（用于画像分析）。"""
        conditions = ["account = ?"]
        params: list = [self._account]
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if intent_type:
            conditions.append("intent_type = ?")
            params.append(intent_type)
        if keyword:
            conditions.append("(nickname LIKE ? OR ip_location LIKE ? OR desc LIKE ?)")
            like = f"%{keyword}%"
            params.extend([like, like, like])

        where = " AND ".join(conditions)
        rows = self._conn.execute(
            f"SELECT * FROM users WHERE {where} "
            "ORDER BY COALESCE(last_seen_at, 0) DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return [dict(r) for r in rows]

    def update_user_intent(self, user_id: str, intent_type: str, is_potential: bool = False) -> None:
        """更新用户的意向类型和潜在用户标记。"""
        self._conn.execute(
            "UPDATE users SET intent_type=?, is_potential=?, updated_at=? "
            "WHERE user_id=? AND account=?",
            (intent_type, 1 if is_potential else 0, _now_iso(), user_id, self._account),
        )
        self._conn.commit()
