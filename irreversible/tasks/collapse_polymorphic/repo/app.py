import taskdb


def connect():
    return taskdb.connect()


def comment_parent(conn, comment_id):
    rows = conn.execute(
        "SELECT parent_type, parent_id FROM comments WHERE id = ?", (comment_id,)
    )
    return (rows[0][0], rows[0][1]) if rows else None


def comment_count(conn):
    return taskdb.as_int(taskdb.one(conn, "SELECT count(*) FROM comments"))
