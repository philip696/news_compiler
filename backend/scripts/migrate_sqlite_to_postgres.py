#!/usr/bin/env python3
"""
Copy application rows from local SQLite (data/geb.db) into Postgres (DATABASE_URL).

Order respects foreign keys: users → bookmarks, likes, weread_* .
Skips legacy wechat_* tables. Safe to re-run on empty remote only (aborts if remote users exist).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


TABLE_ORDER = [
    "users",
    "bookmarks",
    "likes",
    "weread_accounts",
    "weread_feeds",
    "weread_articles",
]


def _reset_sequences(dst: Engine, inspector) -> None:
    """Align Postgres SERIAL with max(id) after bulk copy."""
    with dst.begin() as conn:
        for tbl in TABLE_ORDER:
            if not inspector.has_table(tbl):
                continue
            cols = [c["name"] for c in inspector.get_columns(tbl)]
            if "id" not in cols:
                continue
            conn.execute(
                text(
                    f'SELECT setval(pg_get_serial_sequence(\'{tbl}\', \'id\'), '
                    f'(SELECT COALESCE(MAX(id), 1) FROM "{tbl}"))'
                )
            )


def migrate(sqlite_url: str, postgres_url: str, force: bool) -> None:
    src = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    dst = create_engine(postgres_url, pool_pre_ping=True)

    with dst.connect() as c:
        n = c.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
    if n > 0 and not force:
        raise SystemExit(
            f"Remote database already has {n} user(s). "
            "Refusing to copy (id collisions). Use --force to copy anyway."
        )

    insp = inspect(dst)

    with src.connect() as sconn, dst.begin() as dconn:
        if force and n > 0:
            for tbl in reversed(TABLE_ORDER):
                if insp.has_table(tbl):
                    dconn.execute(text(f'DELETE FROM "{tbl}"'))

        for tbl in TABLE_ORDER:
            if not insp.has_table(tbl):
                print(f"skip {tbl} (missing on destination)")
                continue
            rows = sconn.execute(text(f'SELECT * FROM "{tbl}"')).mappings().all()
            if not rows:
                print(f"{tbl}: 0 rows")
                continue
            cols = list(rows[0].keys())
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(f":{c}" for c in cols)
            ins = text(f'INSERT INTO "{tbl}" ({col_list}) VALUES ({placeholders})')
            for r in rows:
                dconn.execute(ins, dict(r))
            print(f"{tbl}: {len(rows)} rows")

    _reset_sequences(dst, inspect(dst))
    print("Sequences updated.")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite",
        default=str(root / "data" / "geb.db"),
        help="Path to SQLite geb.db",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing rows in destination app tables, then copy.",
    )
    args = parser.parse_args()

    pg = os.getenv("DATABASE_URL", "")
    if not pg.startswith("postgresql"):
        raise SystemExit("DATABASE_URL must be a postgresql:// URI (check .env).")

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.is_file():
        raise SystemExit(f"SQLite file not found: {sqlite_path}")

    sqlite_url = f"sqlite:///{sqlite_path}"
    migrate(sqlite_url, pg, args.force)


if __name__ == "__main__":
    main()
