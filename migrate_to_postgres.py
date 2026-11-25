"""One-time script: copy the data from the old SQLite file (library.db) into PostgreSQL."""
import os
import sqlite3
import sys
import database

TABLES = [
    ("members", ["id", "name", "status"]),
    ("books", ["id", "title", "author", "available"]),
    ("loans", ["id", "member_id", "book_id", "borrow_date", "due_date", "returned"]),
]


def migrate(sqlite_file="library.db"):
    if not os.path.exists(sqlite_file):
        sys.exit("File not found: " + sqlite_file)
    source = sqlite3.connect(sqlite_file)
    target = database.connect()
    database.create_schema(target)
    c = target.cursor()

    for table, columns in TABLES:
        names = ",".join(columns)
        marks = ",".join("?" * len(columns))
        rows = source.execute("SELECT " + names + " FROM " + table).fetchall()
        for row in rows:
            c.execute(
                "INSERT INTO " + table + "(" + names + ") VALUES(" + marks + ") "
                "ON CONFLICT DO NOTHING",
                row,
            )
        print(table + ": copied", len(rows), "rows")

    # loans.id is a SERIAL column. Move its counter past the copied ids,
    # otherwise the next new loan would reuse an id that already exists.
    c.execute(
        "SELECT setval(pg_get_serial_sequence('loans', 'id'), "
        "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM loans"
    )
    target.commit()
    target.close()
    source.close()


if __name__ == "__main__":
    migrate(sys.argv[1] if len(sys.argv) > 1 else "library.db")
