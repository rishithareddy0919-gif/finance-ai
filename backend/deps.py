from db import get_conn


def get_db():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
