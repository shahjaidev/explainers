import os
import sqlite3


def connect():
    return sqlite3.connect(os.environ.get("TASK_DB", "../db.sqlite"))


def comment_parent(conn, comment_id):
    row = conn.execute(
        "SELECT parent_type, parent_id FROM comments WHERE id = ?", (comment_id,)
    ).fetchone()
    return (row[0], row[1]) if row else None


def comment_count(conn):
    return conn.execute("SELECT count(*) FROM comments").fetchone()[0]
