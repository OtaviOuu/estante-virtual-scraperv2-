# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import sqlite3


import sqlite3


class SQLitePipeline:
    def open_spider(self, spider):
        self.conn = sqlite3.connect("books.db")
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                book_title TEXT,
                book_description TEXT,
                book_price REAL,
                condition TEXT,
                category TEXT,
                author TEXT,
                language TEXT,
                publisher TEXT,
                year TEXT,
                isbn TEXT,
                id TEXT
            )
            """
        )

    def close_spider(self, spider):
        self.conn.commit()
        self.conn.close()

    def process_item(self, item, spider):
        self.cursor.execute(
            """
            INSERT INTO books (
                book_title,
                book_description,
                book_price,
                condition,
                category,
                author,
                language,
                publisher,
                year,
                isbn,
                id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                item["book_title"],
                item["book_description"],
                item["book_price"],
                item["condition"],
                item["category"],
                item["author"],
                item["language"],
                item["publisher"],
                item["year"],
                item["isbn"],
                item["id"],
            ),
        )

        self.conn.commit()
        return item
