import pandas as pd
from flask import jsonify, request

CSV_PATH = "data/silver/books.csv"


class Extract:
    def load_books(self):
        df = pd.read_csv(CSV_PATH)
        df["id"] = df["id"].astype(int)
        return df

    def get_books(self):
        df = self.load_books()
        return jsonify(df.to_dict(orient="records")), 200

    def get_book(self, book_id):
        df = self.load_books()
        book = df.loc[df["id"] == book_id]
        if book.empty:
            return jsonify({"error": "Livro não encontrado"}), 404
        return jsonify(book.iloc[0].to_dict()), 200

    def search_books(self):
        df = self.load_books()
        title = request.args.get("title", "").lower()
        category = request.args.get("category", "").lower()

        if title:
            df = df[df["title"].str.lower().str.contains(title, na=False)]
        if category:
            df = df[df["category"].str.lower().str.contains(category, na=False)]

        return jsonify(df.to_dict(orient="records")), 200

    def get_categories(self):
        df = self.load_books()
        categories = sorted(df["category"].dropna().unique().tolist())
        return jsonify(categories), 200
