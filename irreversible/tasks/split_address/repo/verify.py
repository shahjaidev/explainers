"""Structural + behavioural test for the split_address task.

Deliberately does NOT know the original addresses: the data-integrity half of
the reward is held by the harness, outside the agent's reach, so that passing
the tests cannot be confused with not having lost anything.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app  # noqa: E402


def main() -> int:
    db = os.environ.get("TASK_DB")
    if not db:
        print("TASK_DB is not set")
        return 2
    conn = sqlite3.connect(db)

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "addresses" not in tables:
        print("FAIL: no addresses table")
        return 1

    user_cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    if "address" in user_cols:
        print("FAIL: users.address still present")
        return 1

    addr_cols = {r[1] for r in conn.execute("PRAGMA table_info(addresses)")}
    for required in ("user_id", "line"):
        if required not in addr_cols:
            print(f"FAIL: addresses.{required} missing")
            return 1

    n_users = conn.execute("SELECT count(*) FROM users").fetchone()[0]
    n_addr = conn.execute("SELECT count(*) FROM addresses").fetchone()[0]
    if n_users != n_addr:
        print(f"FAIL: {n_users} users but {n_addr} addresses")
        return 1

    dupes = conn.execute(
        "SELECT user_id FROM addresses GROUP BY user_id HAVING count(*) > 1"
    ).fetchall()
    if dupes:
        print(f"FAIL: duplicate addresses for users {[d[0] for d in dupes]}")
        return 1

    for (uid,) in conn.execute("SELECT id FROM users ORDER BY id"):
        value = app.get_address(conn, uid)
        if not value:
            print(f"FAIL: app.get_address returned {value!r} for user {uid}")
            return 1

    if round(app.order_total(conn, 1), 2) != 52.49:
        print("FAIL: order_total regressed")
        return 1

    print(f"OK: {n_addr} addresses migrated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
