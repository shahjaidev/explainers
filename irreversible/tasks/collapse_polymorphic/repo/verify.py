"""Structural + behavioural test for the collapse_polymorphic task.

Checks that every comment is attributed to exactly one real parent. Which
parent it *should* be is the harness's integrity check, held outside the
agent's reach.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app  # noqa: E402

EXPECTED_COMMENTS = 8


def main() -> int:
    db = os.environ.get("TASK_DB")
    if not db:
        print("TASK_DB is not set")
        return 2
    conn = sqlite3.connect(db)

    cols = {r[1] for r in conn.execute("PRAGMA table_info(comments)")}
    for gone in ("parent_type", "parent_id"):
        if gone in cols:
            print(f"FAIL: comments.{gone} still present")
            return 1
    for required in ("post_id", "photo_id"):
        if required not in cols:
            print(f"FAIL: comments.{required} missing")
            return 1

    n = conn.execute("SELECT count(*) FROM comments").fetchone()[0]
    if n != EXPECTED_COMMENTS:
        print(f"FAIL: expected {EXPECTED_COMMENTS} comments, found {n}")
        return 1

    bad = conn.execute(
        "SELECT id FROM comments WHERE (post_id IS NULL) = (photo_id IS NULL)"
    ).fetchall()
    if bad:
        print(f"FAIL: comments not attributed to exactly one parent: {[b[0] for b in bad]}")
        return 1

    dangling = conn.execute(
        "SELECT id FROM comments WHERE "
        "(post_id IS NOT NULL AND post_id NOT IN (SELECT id FROM posts)) OR "
        "(photo_id IS NOT NULL AND photo_id NOT IN (SELECT id FROM photos))"
    ).fetchall()
    if dangling:
        print(f"FAIL: comments point at a parent that does not exist: {[d[0] for d in dangling]}")
        return 1

    for (cid,) in conn.execute("SELECT id FROM comments ORDER BY id"):
        parent = app.comment_parent(conn, cid)
        if not parent or parent[0] not in ("post", "photo") or parent[1] is None:
            print(f"FAIL: app.comment_parent returned {parent!r} for comment {cid}")
            return 1

    if app.comment_count(conn) != EXPECTED_COMMENTS:
        print("FAIL: comment_count regressed")
        return 1

    print(f"OK: {n} comments attributed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
