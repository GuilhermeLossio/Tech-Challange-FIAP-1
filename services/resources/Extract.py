from services.api.src.app import get_book

class extract:
    def get_book(self, book_id):
        return get_book(book_id)