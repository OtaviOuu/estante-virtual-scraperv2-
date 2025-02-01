import questionary
from selectolax.parser import HTMLParser
import requests
import subprocess


def get_categories():
    url = "https://www.estantevirtual.com.br/categoria"
    response = requests.get(
        url, headers={"User-Agent": "Mozilla/5.0", "Cookie": "foo=bar"}
    )
    tree = HTMLParser(response.text)
    categories = tree.css(".estantes-list-container ul li a")
    return [c.attrs["href"][1:] for c in categories]


def select():
    categorias = get_categories()
    selecionadas = questionary.checkbox(
        "escolhe as categorias ai", choices=categorias
    ).ask()

    return selecionadas


def run_scrapy(categories):
    categories_str = ",".join(categories)
    subprocess.run(
        ["scrapy", "crawl", "estantevirtual", "-a", f"categories={categories_str}"]
    )


if __name__ == "__main__":
    selected_categories = select()
    if selected_categories:
        run_scrapy(selected_categories)
