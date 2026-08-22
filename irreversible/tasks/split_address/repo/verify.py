"""Structural + behavioural test for the split_address task.

Deliberately does NOT know the original addresses: the data-integrity half of
the reward is held by the harness, outside the agent's reach, so that passing
the tests cannot be confused with not having lost anything.

Runs unchanged on SQLite and Postgres via taskdb.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app  # noqa: E402
import taskdb  # noqa: E402


def main() -> int:
    conn = taskdb.connect()

    if "addresses" not in taskdb.tables(conn):
        print("FAIL: no addresses table")
        return 1

    if "address" in taskdb.columns(conn, "users"):
        print("FAIL: users.address still present")
        return 1

    addr_cols = taskdb.columns(conn, "addresses")
    for required in ("user_id", "line"):
        if required not in addr_cols:
            print(f"FAIL: addresses.{required} missing")
            return 1

    n_users = taskdb.as_int(taskdb.one(conn, "SELECT count(*) FROM users"))
    n_addr = taskdb.as_int(taskdb.one(conn, "SELECT count(*) FROM addresses"))
    if n_users != n_addr:
        print(f"FAIL: {n_users} users but {n_addr} addresses")
        return 1

    dupes = conn.execute(
        "SELECT user_id FROM addresses GROUP BY user_id HAVING count(*) > 1"
    )
    if dupes:
        print(f"FAIL: duplicate addresses for users {[d[0] for d in dupes]}")
        return 1

    for row in conn.execute("SELECT id FROM users ORDER BY id"):
        value = app.get_address(conn, row[0])
        if not value:
            print(f"FAIL: app.get_address returned {value!r} for user {row[0]}")
            return 1

    if round(float(app.order_total(conn, 1)), 2) != 52.49:
        print("FAIL: order_total regressed")
        return 1

    print(f"OK: {n_addr} addresses migrated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
