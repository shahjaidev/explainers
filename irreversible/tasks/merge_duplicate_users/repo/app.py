import taskdb


def connect():
    return taskdb.connect()


def order_owner(conn, order_id):
    rows = conn.execute(
        "SELECT u.email FROM orders o JOIN users u ON u.id = o.user_id WHERE o.id = ?",
        (order_id,),
    )
    return rows[0][0] if rows else None


def customer_total(conn, email):
    return taskdb.one(
        conn,
        "SELECT coalesce(sum(o.total), 0) FROM orders o "
        "JOIN users u ON u.id = o.user_id WHERE u.email = ?",
        (email,),
    )
