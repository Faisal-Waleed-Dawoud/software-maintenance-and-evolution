from datetime import datetime, timedelta
import database
from library import LibraryRepository
from models import Member, Book

MAX_LOANS = 3
LOAN_PERIOD_DAYS = 14



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

    with LibraryRepository(db) as library :

        member = library.find_member(member_id)
        
        is_valid_member = check_member(member)

        if (not is_valid_member): 
            return False

        book = library.find_book(book_id)

        is_valid_book = check_book(book)
        
        if (not is_valid_book): 
            return False

        count = library.count_active_loans(member_id)

        is_valid_loans_count = check_active_loans_count(count)

        if (not is_valid_loans_count):
            return False

        borrowed_copies = library.count_active_loans_for_book(member_id, book_id)

        can_borrow = check_borrowed_copies(borrowed_copies)

        if (not can_borrow): 
            return False

        today = datetime.now()
        due = today + timedelta(days=LOAN_PERIOD_DAYS)

        
        library.create_loan(member_id, book_id, today.isoformat(), due.isoformat())

    print("Book borrowed. Due:", due.date())

    return True



def check_member(member: Member):
    if not member:
        print("Member not found")
        return False
    
    if not member.is_active():
        print("Member is not active")
        return False 
    return True


def check_book(book: Book): 
    if not book:
        print("Book not found")
        return False
    
    if not book.is_available():
        print("Book is unavailable")
        return False
    
    return True

def check_active_loans_count(active_loans): 
    

    if active_loans >= MAX_LOANS: 
        print("Borrowing limit reached")
        return False
    
    return True

def check_borrowed_copies(copies): 
    if copies > 0: 
        print("You already borrowed a copy of this book.")
        return False

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