import taskdb


def connect():
    return taskdb.connect()


def get_address(conn, user_id):
    rows = conn.execute("SELECT address FROM users WHERE id = ?", (user_id,))
    return rows[0][0] if rows else None


def order_total(conn, user_id):
    return taskdb.one(
        conn, "SELECT coalesce(sum(total), 0) FROM orders WHERE user_id = ?", (user_id,)
    )
