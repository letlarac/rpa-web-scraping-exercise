from decimal import Decimal, InvalidOperation
from typing import TypedDict
from urllib.parse import urljoin

from playwright.sync_api import Page, Locator

URL: str = "https://books.toscrape.com/"


class BookData(TypedDict):
    url: str
    name: str
    rating: int
    price: Decimal
    in_stock: bool


def scrape_books(page: Page, *, category: str | None, max_books: int) -> list[BookData]:
    if max_books <= 0:
        return []

    books: list[BookData] = []

    page.goto(URL)

    if category is not None:
        if not category.strip():
            return []

        categories = page.locator(".side_categories ul li ul li a")

        category_found = False

        for i in range(categories.count()):
            category_link = categories.nth(i)
            category_name = category_link.text_content()

            if category_name is not None:
                if category_name.strip().lower() == category.strip().lower():
                    category_found = True
                    category_link.click()
                    break
        if not category_found:
            return []

    while True:
        cards = page.locator(".product_pod")

        for i in range(cards.count()):
            book = extract_book(cards.nth(i))

            books.append(book)
            if len(books) == max_books:
                break

        if len(books) >= max_books:
            break

        next_page = page.locator("li.next a")
        if next_page.count() == 0:
            break
        next_page.click()

    return books


def extract_book(card: Locator) -> BookData:
    link = card.locator("h3 a")
    name = link.get_attribute("title")

    if name is None or not name.strip():
        raise ValueError("Book title not found.")

    path = link.get_attribute("href")
    if path is None or not path.strip():
        raise ValueError("Book path not found.")

    # Resolve relative links against the current page URL to support pagination.
    absolute_url = urljoin(card.page.url, path)

    price = card.locator(".price_color").text_content()

    if price is None:
        raise ValueError("Book price not found.")

    clean_price = ""

    for character in price:
        if character.isdigit() or character == ".":
            clean_price += character

    if not clean_price:
        raise ValueError("Book price is empty.")

    try:
        numeric_price = Decimal(clean_price)
    except InvalidOperation:
        raise ValueError("Invalid book price.")

    rating_class = card.locator(".star-rating").get_attribute("class")

    if rating_class is None:
        raise ValueError("Book rating is not valid.")

    rating_map = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5,
    }

    rating_split = rating_class.split()
    if len(rating_split) < 2:
        raise ValueError("Book rating is not valid.")
    rating = rating_map.get(rating_split[1])
    if rating is None:
        raise ValueError("Book rating is not valid.")

    stock_text = card.locator(".availability").text_content()

    if stock_text is None or not stock_text.strip():
        raise ValueError("Book availability is not valid.")

    stock_text = stock_text.strip().lower()
    if stock_text == "in stock":
        in_stock = True
    elif stock_text == "out of stock":
        in_stock = False
    else:
        raise ValueError("Book availability is not valid.")

    book: BookData = {
        "url": absolute_url,
        "name": name,
        "rating": rating,
        "price": numeric_price,
        "in_stock": in_stock,
    }

    return book
