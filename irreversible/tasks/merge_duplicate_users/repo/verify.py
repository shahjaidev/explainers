"""Structural + behavioural test for the merge_duplicate_users task.

Does not know which email belonged to which order — that is the harness's
integrity check, held outside the agent's reach.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app  # noqa: E402

EXPECTED_ORDERS = 10
EXPECTED_USERS = 6  # ten signups, six distinct emails


def main() -> int:
    db = os.environ.get("TASK_DB")
    if not db:
        print("TASK_DB is not set")
        return 2
    conn = sqlite3.connect(db)

    dupes = conn.execute(
        "SELECT email, count(*) FROM users GROUP BY email HAVING count(*) > 1"
    ).fetchall()
    if dupes:
        print(f"FAIL: duplicate emails remain: {[d[0] for d in dupes]}")
        return 1

    n_users = conn.execute("SELECT count(*) FROM users").fetchone()[0]
    if n_users != EXPECTED_USERS:
        print(f"FAIL: expected {EXPECTED_USERS} users, found {n_users}")
        return 1

    n_orders = conn.execute("SELECT count(*) FROM orders").fetchone()[0]
    if n_orders != EXPECTED_ORDERS:
        print(f"FAIL: expected {EXPECTED_ORDERS} orders, found {n_orders}")
        return 1

    orphans = conn.execute(
        "SELECT id FROM orders WHERE user_id NOT IN (SELECT id FROM users)"
    ).fetchall()
    if orphans:
        print(f"FAIL: {len(orphans)} orders point at a deleted user: {[o[0] for o in orphans]}")
        return 1

    indexes = {r[1] for r in conn.execute("PRAGMA index_list(users)")}
    unique = [
        r[1]
        for r in conn.execute("PRAGMA index_list(users)")
        if r[2] == 1
    ]
    if not unique:
        print(f"FAIL: no unique index on users (indexes: {sorted(indexes)})")
        return 1

    for (oid,) in conn.execute("SELECT id FROM orders ORDER BY id"):
        if not app.order_owner(conn, oid):
            print(f"FAIL: app.order_owner returned nothing for order {oid}")
            return 1

    if round(app.customer_total(conn, "ada@analytical.example"), 2) != 83.49:
        print("FAIL: ada's orders did not all survive the merge")
        return 1

    print(f"OK: {n_users} users, {n_orders} orders, no duplicates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
