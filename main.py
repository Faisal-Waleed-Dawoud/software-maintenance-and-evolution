
import sqlite3
from datetime import datetime, timedelta
DB = "library.db"
def setup():
    db = sqlite3.connect(DB)
    c = db.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS members(
        id TEXT PRIMARY KEY,
        name TEXT,
        status TEXT
    )
""")

# MR-01: Modified creating the books table to add the max_copies column
    c.execute("""
    CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY,
        title TEXT,
        author TEXT,
        available INTEGER,
        max_copies INTEGER DEFAULT 1
    )
""")

# MR-01: Checks if the max_copies column exists in the table or not. Adds the column if it doesn't exist.
    c.execute("PRAGMA table_info(books)")
    columns = [row[1] for row in c.fetchall()]
    if "max_copies" not in columns:
        c.execute("ALTER TABLE books ADD COLUMN max_copies INTEGER DEFAULT 1")

    c.execute("""
    CREATE TABLE IF NOT EXISTS loans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT,
        book_id INTEGER,
        borrow_date TEXT,
        due_date TEXT,
        returned INTEGER
    )
""")

    db.commit()

    c.execute(
    "INSERT OR IGNORE INTO members VALUES ('S1','Ali','ACTIVE')"
    )

    c.execute(
    "INSERT OR IGNORE INTO members VALUES ('S2','Sara','ACTIVE')"
    )

# MR-01: Added a max_copies value to the books table INSERTs
    c.execute(
    "INSERT OR IGNORE INTO books VALUES (1, 'Clean Code', 'Robert Martin', 3, 3)"
    )

    c.execute(
    "INSERT OR IGNORE INTO books VALUES (2, 'Refactoring','Martin Fowler', 5, 5)"
    )

    c.execute(
    "INSERT OR IGNORE INTO books VALUES (3, 'Design Patterns', 'Gamma et al.', 1, 1)"
    )

    db.commit()
    return db

def search_books(db, text):
    c = db.cursor()
# MR-01: Added max_copies to the SELECT
    c.execute(
    """SELECT id,title,author,available,max_copies
       FROM books
       WHERE title LIKE ? OR author LIKE ?""",
    ("%" + text + "%", "%" + text + "%")
)

    rows = c.fetchall()

# MR-01: Removed the bool cast and made the result show the amount of max copies.
    for row in rows:
        print(row[0], row[1], "-", row[2],
            "Available:", row[3], "/", row[4])

    return rows

def borrow(db, member_id, book_id):
    c = db.cursor()
    c.execute(
    "SELECT id,status FROM members WHERE id=?",
    (member_id,)
)

    member = c.fetchone()

    if not member:
        print("Member not found")
        return False

    if member[1] != "ACTIVE":
        print("Member is not active")
        return False

    c.execute(
    "SELECT available FROM books WHERE id=?",
    (book_id,)
)

    book = c.fetchone()

    if not book:
        print("Book not found")
        return False

    if book[0] == 0:
        print("Book is unavailable")
        return False

# MR-01: Modified the check to make sure a member can only borrow one copy of a book
    c.execute(
    """SELECT COUNT(*) FROM loans
       WHERE member_id=? AND returned=0 AND book_id=?""",
    (member_id, book_id)
    )

    if c.fetchone()[0] > 0:
        print("You already borrowed a copy of this book.")
        return False

    today = datetime.now()
    due = today + timedelta(days=14)

    c.execute(
    """INSERT INTO loans
       (member_id,book_id,borrow_date,due_date,returned)
       VALUES(?,?,?,?,0)""",
    (
        member_id,
        book_id,
        today.isoformat(),
        due.isoformat()
    )
)

# MR-01: Decrement available instead of setting it to 0
    c.execute(
    "UPDATE books SET available = available-1 WHERE id=?",
    (book_id,)
    )

    db.commit()

    print("Book borrowed. Due:", due.date())

    return True

def return_book(db, member_id, book_id):
    c = db.cursor()
    c.execute(
    """SELECT id,due_date FROM loans
       WHERE member_id=? AND book_id=? AND returned=0""",
    (member_id, book_id)
)

    loan = c.fetchone()

    if not loan:
        print("Active loan not found")
        return False

    loan_id = loan[0]
    due = datetime.fromisoformat(loan[1])
    today = datetime.now()

    late = (today - due).days
    fine = late if late > 0 else 0

    c.execute(
        "UPDATE loans SET returned=1 WHERE id=?",
        (loan_id,)
    )

# MR-01: Increments available only if it is less than max_copies
    c.execute(
        "UPDATE books SET available = available+1 WHERE id=? AND available < max_copies",
        (book_id,)
    )

    db.commit()

    print("Book returned")

    if fine:
        print("Fine:", fine)

    return True
def main():
    db = setup()
    while True:
        print("\nLIBRARY")
        print("1 Search")
        print("2 Borrow")
        print("3 Return")
        print("4 Exit")

        choice = input("Choice: ")

        if choice == "1":
            text = input("Search: ")
            search_books(db, text)

        elif choice == "2":
            member = input("Member ID: ")
            book = int(input("Book ID: "))
            borrow(db, member, book)

        elif choice == "3":
            member = input("Member ID: ")
            book = int(input("Book ID: "))
            return_book(db, member, book)

        elif choice == "4":
            db.close()
            break

        else:
            print("Invalid choice")
if __name__ == "__main__":
    main()