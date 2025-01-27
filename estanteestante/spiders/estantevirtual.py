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
        category = book_product["department"]["name"]
        book_title = book_product["name"]

        group_title = book_json["name"]
        book_description = book_json["longDescription"]
        try:
            book_price = book_json["prices"][0][
                "finalPriceWithoutPaymentBenefitDiscount"
            ]
        except Exception as e:
            book_price = book_json["price"]["finalPriceWithoutPaymentBenefitDiscount"]
        author = book_product["author"]
        group_id = "-".join(response.url.split("-")[-4:])

        yield {
            "url": response.url,
            "group_id": group_id,
            "book_title": book_title,
            "group_title": group_title,
            "book_description": book_description,
            "book_price": book_price,
            "category": category,
            "author": author,
        }

    def parse_group_api(self, response: Response):
        json_data = json.loads(response.text)
        total_in_group = json_data["total"]

        group_books = json_data["parentSkus"]
        for book in group_books:
            book_title = book["name"]
            book_id = book["productCode"]
            book_price = int(book["listPrice"]) / 100
            item_group_id = book["itemGroupId"]
            iamges = {
                "image": book["image"],
                "image_detail": book["imageDetail"],
                "image_zoom": book["imageZoom"],
            }
            attributes = book["attributes"]

            yield {
                "total_in_group": total_in_group,
                "book_title": book_title,
                "book_id": book_id,
                "book_price": book_price,
                "item_group_id": item_group_id,
                "images": iamges,
                "attributes": attributes,
            }
