import requests
import json
import math
import pandas as pd
from datetime import datetime
from loguru import logger
from bs4 import BeautifulSoup
from sqlalchemy import Engine
from ._pet_products_etl import PetProductsETL
from .utils import execute_query, update_url_scrape_status, get_sql_from_file

from fake_useragent import UserAgent


class TheNaturalPetStoreETL(PetProductsETL):

    def __init__(self):
        super().__init__()
        self.SHOP = "TheNaturalPetStore"
        self.BASE_URL = "https://www.thenaturalpetstore.co.uk"
        self.CATEGORIES = [
            "/collections/dogs",
            "/collections/cat",
            "/collections/small-pets",
            "/collections/birds",
            "/collections/pic-n-mix",
        ]

    def get_links(self, category: str) -> pd.DataFrame:
        if category not in self.CATEGORIES:
            raise ValueError(
                f"Invalid category. Value must be in {self.CATEGORIES}")

        url = self.BASE_URL+category
        soup = self.extract_from_url("GET", url)
        n_product = int(soup.find(
            'p', class_="collection__products-count-total").get_text().replace(' products', ''))
        pagination_length = math.ceil(n_product / 24)
        urls = []

        for i in range(1, pagination_length + 1):
            soup_pagination = self.extract_from_url("GET", f"{url}?page={i}")
            for prod_list in soup_pagination.find_all('div', class_="product-item--vertical"):
                urls.append(self.BASE_URL + prod_list.find('a').get('href'))

        df = pd.DataFrame({"url": urls})
        df.insert(0, "shop", self.SHOP)
        return df

    def transform(self, soup: BeautifulSoup, url: str):
        try:
            product_name = soup.find(
                'h1', class_="product-meta__title").get_text()
            product_description = None

            if soup.find('div', class_="product-block-list__item--description"):
                product_description = soup.find('div', class_="product-block-list__item--description").find(
                    'div', class_="text--pull").get_text(strip=True)

            product_url = url.replace(self.BASE_URL, "")
            product_rating = '0/5'

            if soup.find('span', class_="rating__caption").get_text() != "No reviews":
                rating_label = soup.find(
                    'div', class_="rating__stars").get('aria-label')

                rating_values = [float(s) for s in rating_label.split(
                ) if s.replace('.', '', 1).isdigit()]
                numerator, denominator = int(
                    rating_values[0]), int(rating_values[1])
                product_rating = f"{numerator}/{denominator}"

            variants = []
            prices = []
            discounted_prices = []
            discount_percentages = []

            headers = {
                "User-Agent": UserAgent().random,
                'Accept': 'application/json'
            }

            product_info = requests.get(url, headers=headers)

            for variant_info in product_info.json()['product']["variants"]:
                variants.append(variant_info.get('title'))
                if (variant_info.get('compare_at_price') != ""):
                    price = float(variant_info.get('compare_at_price'))
                    discount_price = float(variant_info.get('price'))
                    discount_percentage = round(
                        (price - discount_price) / price, 2)

                    prices.append(price)
                    discounted_prices.append(discount_price)
                    discount_percentages.append(discount_percentage)
                else:
                    prices.append(variant_info.get('price'))
                    discounted_prices.append(None)
                    discount_percentages.append(None)

            df = pd.DataFrame({"variant": variants, "price": prices,
                               "discounted_price": discounted_prices, "discount_percentage": discount_percentages})
            df.insert(0, "url", product_url)
            df.insert(0, "description", product_description)
            df.insert(0, "rating", product_rating)
            df.insert(0, "name", product_name)
            df.insert(0, "shop", self.SHOP)

            return df
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
