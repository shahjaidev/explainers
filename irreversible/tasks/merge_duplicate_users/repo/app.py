import os
import sqlite3


def connect():
    return sqlite3.connect(os.environ.get("TASK_DB", "../db.sqlite"))


def order_owner(conn, order_id):
    row = conn.execute(
        "SELECT u.email FROM orders o JOIN users u ON u.id = o.user_id WHERE o.id = ?",
        (order_id,),
    ).fetchone()
    return row[0] if row else None


def customer_total(conn, email):
    row = conn.execute(
        "SELECT coalesce(sum(o.total), 0) FROM orders o "
        "JOIN users u ON u.id = o.user_id WHERE u.email = ?",
        (email,),
    ).fetchone()
    return row[0]
