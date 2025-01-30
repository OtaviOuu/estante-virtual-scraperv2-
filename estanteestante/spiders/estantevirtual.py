from scrapy import Spider, Request
from scrapy.http import Response

import json
import re


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


class EstantevirtualSpider(Spider):
    name = "estantevirtual"
    allowed_domains = ["estantevirtual.com.br"]
    base_url = "https://www.estantevirtual.com.br"

    def __init__(self, categories=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.categories = categories.split(",")

    def start_requests(self):
        for category in self.categories:

            for condition in ["usado", "novo"]:
                yield Request(
                    url=f"{self.base_url}/busca?categoria={category}&tipo-de-livro={condition}",
                    callback=self.parse_authors,
                    meta={"condition": condition},
                )

                yield Request(
                    url=f"{self.base_url}/{category}?tipo-de-livro={condition}",
                    callback=self.parse_authors,
                    meta={"condition": condition},
                )

    # bypass do limite
    def parse_authors(self, response: Response):
        initial_state = json.loads(
            response.css("script")[-4]
            .get()
            .strip()
            .replace("<script>window.__INITIAL_STATE__=", "")
            .replace("</script>", "")
        )

        editoras = initial_state["SearchPage"]["normalizedAggregates"]["editora"][
            "filters"
        ]

        for editora in editoras:
            editora_slug = editora["value"]

            url_with_editora = f"{response.url}&editora={editora_slug}"

            yield Request(
                url=url_with_editora,
                callback=self.parse_pagination,
                meta={"condition": response.meta["condition"]},
            )

    def parse_pagination(self, response: Response):
        results = response.css(".product-list-header__sort__text::text").get()
        if results:
            try:
                query_result = int(
                    results.strip()
                    .split("de ")[1]
                    .split(" resultados")[0]
                    .replace(".", "")
                )
                last_page_index = min(query_result // 44, 682)
            except ValueError:
                last_page_index = 1
            for index in range(1, last_page_index + 1):
                url = f"{response.url}&page={index}"

                yield Request(
                    url=url,
                    callback=self.parse_links,
                    meta={"condition": response.meta["condition"]},
                )

    def parse_links(self, response: Response):
        urls = response.css(".product-list__items #product-item a::attr(href)").getall()
        for url in urls:
            yield Request(
                url=f"{self.base_url}{url}",
                callback=self.parse_group_book,
                meta={"condition": response.meta["condition"]},
            )

    def parse_group_book(self, response: Response):
        if "000-BK" in response.url:
            group_id = "-".join(response.url.split("-")[-4:])
            api = f"{self.base_url}/pdp-api/api/searchProducts/{group_id}/{response.meta['condition']}?pageSize=999&page=1&sort=lowest-first"

            yield Request(
                url=api,
                callback=self.parse_group_api,
                meta={"condition": response.meta["condition"]},
            )
            return

        # bizarro, mas regex ta meio mé...
        json_data = json.loads(
            response.css("script")[-3]
            .get()
            .strip()
            .replace("<script>window.__INITIAL_STATE__=", "")
            .replace("</script>", "")
        )

        try:
            book_product = json_data["json"]["Product"]

        except Exception as e:
            book_product = json_data["Product"]

        book_json = book_product["parents"][0]["skus"][0]
        category = book_product["department"].get("name", "")
        book_title = book_product["name"]

        attributes = book_product["templateAttributes"]
        attribute_map = {
            attribute.get("name", "").lower(): attribute.get("value", "")
            for attribute in attributes
        }

        author = attribute_map.get("author", "")
        language = attribute_map.get("language", "")
        publisher = attribute_map.get("publisher", "")
        year = attribute_map.get("year", "")
        isbn = attribute_map.get("isbn", "")

        book_description = book_json["longDescription"]
        try:
            book_price = book_json["prices"][0][
                "finalPriceWithoutPaymentBenefitDiscount"
            ]
        except Exception as e:
            book_price = book_json["price"]["finalPriceWithoutPaymentBenefitDiscount"]
        author = book_product["author"]

        yield {
            "book_title": book_title,
            "book_description": book_description,
            "book_price": int(book_price) / 100,
            "condition": response.meta["condition"],
            "category": category,
            "author": author,
            "language": language,
            "publisher": publisher,
            "year": year,
            "isbn": isbn,
            "id": "-".join(response.url.split("-")[-3:]),
        }

    def parse_group_api(self, response: Response):
        json_data = json.loads(response.text)

        group_books = json_data["parentSkus"]
        for book in group_books:
            book_title = book["name"]
            book_id = book["productCode"]
            book_price = int(book["listPrice"]) / 100

            attributes = {
                attr.get("name", "").lower(): attr.get("value", "")
                for attr in book["attributes"]
            }
            author = attributes.get("author", "")
            language = attributes.get("language", "")
            publisher = attributes.get("publisher", "")
            year = attributes.get("year", "")
            isbn = attributes.get("isbn", "")

            yield {
                "book_title": book_title,
                "book_description": book["description"],
                "book_price": book_price,
                "condition": response.meta["condition"],
                "category": book["department"],
                "author": author,
                "language": language,
                "publisher": publisher,
                "year": year,
                "isbn": isbn,
                "id": book_id,
            }
