from models import Book, Member

class LibraryRepository: 

    def __init__(self, db):
        self.db = db
        self.cursor = None

    def __enter__(self): 
        self.cursor = self.db.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.db.commit()
        else:
            self.db.rollback()

    def find_member(self, member_id):

        query = "SELECT id,status FROM members WHERE id=?"

        self.cursor.execute(
            query,
            (member_id,))

        member = self.cursor.fetchone()

        return Member(member[0], member[1]) if member else None

    def find_book(self, book_id): 

        query = "SELECT available FROM books WHERE id=?"
        
        self.cursor.execute(
            query,
            (book_id,))
        
        book = self.cursor.fetchone()

        return Book(book_id, book[0]) if book else None

    def count_active_loans(self, member_id): 


        query = """SELECT COUNT(*) FROM loans
                WHERE member_id=? AND returned=0"""

        self.cursor.execute(
            query,
            (member_id,)
        )

        active_loans = self.cursor.fetchone()[0]

        return active_loans

    def create_loan(self, member_id, book_id, borrow_date, due_date): 
        query = """INSERT INTO loans
        (member_id,book_id,borrow_date,due_date,returned)
        VALUES(?,?,?,?,0)"""
        
        self.cursor.execute(query, 
        (member_id,
        book_id,
        borrow_date,
        due_date))

        query = "UPDATE books SET available = available-1 WHERE id=?"

        self.cursor.execute(query, (book_id,))

    def count_active_loans_for_book(self, member_id, book_id): 
        query = """SELECT COUNT(*) FROM loans
        WHERE member_id=? AND returned=0 AND book_id=?"""

        self.cursor.execute(query, (member_id, book_id))

        borrowed_copies = self.cursor.fetchone()[0]

        return borrowed_copies
