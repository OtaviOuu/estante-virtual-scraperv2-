from scrapy import Spider, Request
from scrapy.http import Response

import json


class EstantevirtualSpider(Spider):
    name = "estantevirtuall"
    allowed_domains = ["estantevirtual.com.br"]
    base_url = "https://www.estantevirtual.com.br"

    def start_requests(self):
        yield Request(
            url=f"{self.base_url}/categoria",
            callback=self.parse_categorys,
        )

    def parse_categorys(self, response: Response):
        categorys = response.css(
            ".estantes-list-container ul li a::attr(href)"
        ).getall()

        for category in categorys:
            url_usada = f"{self.base_url}{category}?tipo-de-livro=usado"
            url_nova = f"{self.base_url}{category}?tipo-de-livro=novo"

            yield Request(
                url=url_usada,
                callback=self.parse_pagination,
                meta={"condition": "usado"},
            )

            yield Request(
                url=url_nova,
                callback=self.parse_pagination,
                meta={"condition": "novo"},
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
            with open("last_page_index.txt", "w") as f:
                f.write(f"{last_page_index}\n")
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
        author = ""
        language = ""
        publisher = ""
        year = ""
        isbn = ""
        for attribute in attributes:
            att_name = attribute.get("name", "")
            if att_name == "author":
                author = attribute.get("value", "")
            elif att_name == "language":
                language = attribute.get("value", "")
            elif att_name == "publisher":
                publisher = attribute.get("value", "")
            elif att_name == "year":
                year = attribute.get("value", "")
            elif att_name == "isbn":
                isbn = attribute.get("value", "")

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

            attributes = book["attributes"]
            author = ""
            language = ""
            publisher = ""
            year = ""
            isbn = ""
            isbn = ""
            for attribute in attributes:
                att_name = attribute.get("name", "")
                if att_name == "author":
                    author = attribute.get("value", "")
                elif att_name == "language":
                    language = attribute.get("value", "")
                elif att_name == "publisher":
                    publisher = attribute.get("value", "")
                elif att_name == "year":
                    year = attribute.get("value", "")
                elif att_name == "isbn":
                    isbn = attribute.get("value", "")

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
