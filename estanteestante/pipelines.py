# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import sqlite3


class SQLitePipeline:
    def open_spider(self, spider):
        self.conn = sqlite3.connect("books.db")
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS books (
            book_title TEXT
        )
        """
        )

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        self.cursor.execute(
            """
            INSERT INTO books (
                book_title
            ) VALUES (?)
            """,
            (item["book_title"],),
        )

        self.conn.commit()
        return item
