"""database.py - the only module that knows which database the library system uses (PostgreSQL)."""
import os
import psycopg2


class Cursor:
    """Wraps a PostgreSQL cursor so the rest of the program can keep using '?' placeholders."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=None):
        self._cursor.execute(sql.replace("?", "%s"), params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class Database:
    """Wraps a PostgreSQL connection. It has the same methods the program already uses."""

    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return Cursor(self._connection.cursor())

    def commit(self):
        self._connection.commit()

    def close(self):
        self._connection.close()


def connect():
    """Open a connection using environment variables (with local defaults)."""
    connection = psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "library"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    )
    return Database(connection)


def create_schema(db):
    """Create the three tables in PostgreSQL if they do not exist yet."""
    c = db.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS members(
            id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS books(
            id INTEGER PRIMARY KEY,
            title TEXT,
            author TEXT,
            available INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS loans(
            id SERIAL PRIMARY KEY,
            member_id TEXT,
            book_id INTEGER,
            borrow_date TEXT,
            due_date TEXT,
            returned INTEGER
        )
    """)
    db.commit()
