import os
from db.connection import get_connection

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def init_db():
    with open(SCHEMA_PATH) as f:
        sql = f.read()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("Schema applied successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
