import pandas as pd
from flask import jsonify, request

CSV_PATH = "data/silver/books.csv"

class Extract:
    def load_books(self):
        df = pd.read_csv(CSV_PATH)
        df["id"] = df["id"] # o id do livro não é numero inteiro
        return df

    def get_books(self):
        df = self.load_books()
        return jsonify(df.to_dict(orient="records")), 200

    def get_book(self, book_id):
        df = self.load_books()
        book = df.loc[df["id"] == book_id]
        if book.empty:
            return {}
        return book.iloc[0].to_dict()

    def search_books(self, title = "", category = ""):
        books = self.load_books()
        results = books[books["title"].str.contains(title, case=False, na=False) & books["category"].str.contains(category, case=False, na=False)]

        return results

    def get_categories(self):
        df = self.load_books()
        categories = sorted(df["category"].dropna().unique().tolist())
        return categories
    
    def get_books_top_rated(self):
        df = self.load_books()
        books = df[df["rating"] == 5]
        return books.fillna("").to_dict(orient="records")

    def get_books_price_range(self, min = 0, max = 0):
        df = self.load_books()
        if min is not None:
            df = df[df["raw_price"] >= min]
        if max is not None:
            df = df[df["raw_price"] <= max]
        return df.fillna("").to_dict(orient="records")

    def get_overview(self, books = None):
        if books.empty:
            books = self.load_books()
        
        average_price = round(books["raw_price"].mean(), 2)
        rating_distribution = books["rating"].value_counts().to_dict()

        stats = {
            "total_books": len(books),
            "average_price": average_price,
            "rating_distribution": rating_distribution
        }

        return stats
    
    def get_category_stats(self):
        categories = self.get_categories()
        stats_category = {}

        for category in categories:
            books = self.search_books(category=category)
            stats_category[category] = self.get_overview(books)

        return stats_category