from datetime import datetime, timedelta
import database
def setup():
    db = database.connect()
    database.create_schema(db)
    c = db.cursor()

    # Seed members
    c.execute(
        "INSERT INTO members VALUES ('S1','Ali','ACTIVE') ON CONFLICT DO NOTHING"
    )
    c.execute(
        "INSERT INTO members VALUES ('S2','Sara','ACTIVE') ON CONFLICT DO NOTHING"
    )


    # MR-01: Seed books with multiple copies
    c.execute(
        "INSERT INTO books (id, title, author, available, max_copies) "
        "VALUES (1, 'Clean Code', 'Robert Martin', 3, 3) ON CONFLICT DO NOTHING"
    )
    c.execute(
        "INSERT INTO books (id, title, author, available, max_copies) "
        "VALUES (2, 'Refactoring', 'Martin Fowler', 5, 5) ON CONFLICT DO NOTHING"
    )
    c.execute(
        "INSERT INTO books (id, title, author, available, max_copies) "
        "VALUES (3, 'Design Patterns', 'Gamma et al.', 1, 1) ON CONFLICT DO NOTHING"
    )

    db.commit()
    return db

def search_books(db, text):
    c = db.cursor()
# MR-01: Added max_copies to the SELECT
    c.execute(
    """SELECT id,title,author,available,max_copies
       FROM books
       WHERE LOWER(title) LIKE LOWER(?) OR LOWER(author) LIKE LOWER(?)""",
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

    c.execute(
        """SELECT COUNT(*) FROM loans
        WHERE member_id=? AND returned=0""",
        (member_id,)
    )

    if c.fetchone()[0] >= 3:
        print("Borrowing limit reached")
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