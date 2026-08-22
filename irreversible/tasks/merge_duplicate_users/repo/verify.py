"""Structural + behavioural test for the merge_duplicate_users task.

Does not know which email belonged to which order — that is the harness's
integrity check, held outside the agent's reach.

Runs unchanged on SQLite and Postgres via taskdb.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app  # noqa: E402
import taskdb  # noqa: E402

EXPECTED_ORDERS = 10
EXPECTED_USERS = 6  # ten signups, six distinct emails


def main() -> int:
    conn = taskdb.connect()

    dupes = conn.execute(
        "SELECT email FROM users GROUP BY email HAVING count(*) > 1"
    )
    if dupes:
        print(f"FAIL: duplicate emails remain: {[d[0] for d in dupes]}")
        return 1

    n_users = taskdb.as_int(taskdb.one(conn, "SELECT count(*) FROM users"))
    if n_users != EXPECTED_USERS:
        print(f"FAIL: expected {EXPECTED_USERS} users, found {n_users}")
        return 1

    n_orders = taskdb.as_int(taskdb.one(conn, "SELECT count(*) FROM orders"))
    if n_orders != EXPECTED_ORDERS:
        print(f"FAIL: expected {EXPECTED_ORDERS} orders, found {n_orders}")
        return 1

    orphans = conn.execute(
        "SELECT id FROM orders WHERE user_id NOT IN (SELECT id FROM users)"
    )
    if orphans:
        print(f"FAIL: {len(orphans)} orders point at a deleted user: {[o[0] for o in orphans]}")
        return 1

    if not taskdb.has_unique_index(conn, "users"):
        print("FAIL: no unique index on users")
        return 1

    for row in conn.execute("SELECT id FROM orders ORDER BY id"):
        if not app.order_owner(conn, row[0]):
            print(f"FAIL: app.order_owner returned nothing for order {row[0]}")
            return 1

    if round(float(app.customer_total(conn, "ada@analytical.example")), 2) != 83.49:
        print("FAIL: ada's orders did not all survive the merge")
        return 1

    print(f"OK: {n_users} users, {n_orders} orders, no duplicates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
