from sqlalchemy import text

from app.db.session import engine


def main():
    statements = [
        "ALTER TABLE pack_header ADD COLUMN IF NOT EXISTS picked_by TEXT DEFAULT ''",
    ]

    with engine.begin() as conn:
        for sql in statements:
            conn.execute(text(sql))

    print('OK: sprint42 pack picker schema migrated')


if __name__ == '__main__':
    main()
