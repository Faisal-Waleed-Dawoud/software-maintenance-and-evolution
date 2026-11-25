"""Tests for MR-02 (PostgreSQL replacement). Runs the real menu in main.py with scripted input.

WARNING: this script DELETES the tables in the test database. It refuses to run on a database named 'library'.
Usage:  createdb library_test   (once)
        python test_mr02.py
"""
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

os.environ.setdefault("PGDATABASE", "library_test")
if os.environ["PGDATABASE"] == "library":
    sys.exit("Refusing to run on the real 'library' database. Use a separate test database.")

import database

HERE = os.path.dirname(os.path.abspath(__file__))
results = []


def run_menu(*inputs):
    """Run main.py and type the given lines into the menu. Returns the program output."""
    text = "\n".join(inputs) + "\n"
    done = subprocess.run([sys.executable, "main.py"], input=text, text=True,
                          capture_output=True, cwd=HERE, timeout=60)
    if done.returncode != 0:
        return done.stdout + done.stderr
    return done.stdout


def sql(query, params=None):
    db = database.connect()
    c = db.cursor()
    c.execute(query, params)
    rows = c.fetchall() if query.lstrip().upper().startswith("SELECT") else None
    db.commit()
    db.close()
    return rows


def reset():
    sql("DROP TABLE IF EXISTS loans")
    sql("DROP TABLE IF EXISTS books")
    sql("DROP TABLE IF EXISTS members")


def check(name, condition, note=""):
    results.append((name, bool(condition)))
    print(name.ljust(62), "PASS" if condition else "FAIL", note)


# ---------- T1 / T2: setup ----------
reset()
run_menu("4")
check("T1 Empty database: tables + sample data created",
      sql("SELECT COUNT(*) FROM members")[0][0] == 2 and sql("SELECT COUNT(*) FROM books")[0][0] == 3
      and sql("SELECT COUNT(*) FROM loans")[0][0] == 0)
run_menu("4")
check("T2 Starting again does not duplicate the sample data",
      sql("SELECT COUNT(*) FROM members")[0][0] == 2 and sql("SELECT COUNT(*) FROM books")[0][0] == 3)

# ---------- T3: search ----------
out = run_menu("1", "clean", "4")
out2 = run_menu("1", "MARTIN", "4")
out3 = run_menu("1", "", "4")
check("T3 Search ignores upper/lower case and also finds authors",
      "Clean Code" in out and "Robert Martin" in out2 and "Martin Fowler" in out2
      and out3.count("Available:") == 3)

# ---------- T4 / T5: borrow ----------
due = (datetime.now() + timedelta(days=14)).date()
out = run_menu("2", "S1", "1", "4")
check("T4 Borrow works: due date printed, loan saved, book unavailable",
      "Book borrowed. Due: " + str(due) in out
      and sql("SELECT COUNT(*) FROM loans WHERE member_id='S1' AND book_id=1 AND returned=0")[0][0] == 1
      and sql("SELECT available FROM books WHERE id=1")[0][0] == 0)
out = run_menu("2", "S2", "1", "4")
check("T5 Borrowing an unavailable book is blocked",
      "Book is unavailable" in out and sql("SELECT COUNT(*) FROM loans")[0][0] == 1)

# ---------- T6: other borrow rules ----------
sql("UPDATE members SET status='INACTIVE' WHERE id='S2'")
out = run_menu("2", "X9", "2", "2", "S2", "2", "2", "S1", "99", "4")
sql("UPDATE members SET status='ACTIVE' WHERE id='S2'")
check("T6 Unknown member, inactive member and unknown book are rejected",
      "Member not found" in out and "Member is not active" in out and "Book not found" in out)

# ---------- T7: loan limit ----------
sql("INSERT INTO books VALUES (4,'Extra Book','Test Author',1)")
out = run_menu("2", "S1", "2", "2", "S1", "3", "2", "S1", "4", "4")
check("T7 Limit of 3 active loans is enforced",
      "Borrowing limit reached" in out
      and sql("SELECT COUNT(*) FROM loans WHERE member_id='S1' AND returned=0")[0][0] == 3)

# ---------- T8 / T9 / T10: return ----------
out = run_menu("3", "S1", "1", "4")
check("T8 On-time return: no fine, loan closed, book available again",
      "Book returned" in out and "Fine:" not in out
      and sql("SELECT returned FROM loans WHERE book_id=1")[0][0] == 1
      and sql("SELECT available FROM books WHERE id=1")[0][0] == 1)
late_due = (datetime.now() - timedelta(days=5)).isoformat()
sql("UPDATE loans SET due_date=? WHERE book_id=2 AND returned=0", (late_due,))
out = run_menu("3", "S1", "2", "4")
check("T9 Late return (5 days): fine of 5 is shown", "Fine: 5" in out)
out = run_menu("3", "S2", "3", "4")
check("T10 Return without an active loan is rejected", "Active loan not found" in out)

# ---------- T11: data survives a restart ----------
out = run_menu("1", "Design", "4")
check("T11 Data is still there after restarting the program", "Available: False" in out)

# ---------- T12: migration from SQLite ----------
reset()
folder = tempfile.mkdtemp()
old_file = os.path.join(folder, "library.db")
old = sqlite3.connect(old_file)
old.executescript("""
CREATE TABLE members(id TEXT PRIMARY KEY, name TEXT, status TEXT);
CREATE TABLE books(id INTEGER PRIMARY KEY, title TEXT, author TEXT, available INTEGER);
CREATE TABLE loans(id INTEGER PRIMARY KEY AUTOINCREMENT, member_id TEXT, book_id INTEGER,
                   borrow_date TEXT, due_date TEXT, returned INTEGER);
INSERT INTO members VALUES ('S1','Ali','ACTIVE'),('S2','Sara','ACTIVE');
INSERT INTO books VALUES (1,'Clean Code','Robert Martin',1),(2,'Refactoring','Martin Fowler',0),
                         (3,'Design Patterns','Gamma et al.',1);
INSERT INTO loans VALUES (1,'S1',1,'2026-11-01T10:00:00','2026-11-15T10:00:00',1),
                         (7,'S1',2,'2026-11-10T10:00:00','2026-11-24T10:00:00',0);
""")
old.commit()
old.close()
done = subprocess.run([sys.executable, "migrate_to_postgres.py", old_file], text=True,
                      capture_output=True, cwd=HERE, timeout=60)
same = (sql("SELECT COUNT(*) FROM members")[0][0] == 2 and sql("SELECT COUNT(*) FROM books")[0][0] == 3
        and sql("SELECT COUNT(*) FROM loans")[0][0] == 2
        and sql("SELECT available FROM books WHERE id=2")[0][0] == 0
        and sql("SELECT due_date FROM loans WHERE id=7")[0][0] == "2026-11-24T10:00:00")
check("T12 Migration copies every row of library.db unchanged", done.returncode == 0 and same, done.stdout.replace("\n", "; "))
out = run_menu("2", "S2", "1", "4")
new_id = sql("SELECT MAX(id) FROM loans")[0][0]
check("T13 After migration a new loan gets a fresh id (no clash)",
      "Book borrowed" in out and new_id == 8 and sql("SELECT COUNT(*) FROM loans")[0][0] == 3,
      "new loan id = " + str(new_id))

failed = [n for n, ok in results if not ok]
print("\n%d of %d tests passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
