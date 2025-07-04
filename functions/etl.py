import os
import json
import asyncio
import pandas as pd

from abc import ABC, abstractmethod
from sqlalchemy.engine import Engine
from .connection import Connection
from .scraper import scrape_url
from loguru import logger
from datetime import datetime as dt


class PetProductsETL(ABC):
    def __init__(self):
        self.SHOP = ""
        self.BASE_URL = ""
        self.SELECTOR_SCRAPE_PRODUCT_INFO = ''
        self.connection = Connection()

    async def scrape(self, url, selector, headers=None):
        soup = await scrape_url(url, selector, headers)
        if soup:
            return soup
        else:
            return False

    @abstractmethod
    def extract(self):
        pass

    @abstractmethod
    def transform(self):
        pass

    def load(self, data: pd.DataFrame, table_name: str):
        try:
            n = data.shape[0]
            data.to_sql(table_name, self.connection.engine,
                        if_exists="append", index=False)
            logger.success(
                f"Successfully loaded {n} records to the {table_name}.")

        except Exception as e:
            logger.error(e)
            raise e

    def get_product_infos(self):
        temp_table = f"stg_{self.SHOP.lower()}_temp_products"
        self.connection.execute_query(f"DROP TABLE IF EXISTS {temp_table};")
        create_temp_sql = self.connection.get_sql_from_file(
            'create_temp_table_product_info.sql')
        create_temp_sql = create_temp_sql.format(
            table_name=temp_table)
        self._temp_table(create_temp_sql, temp_table, 'created')

        sql = self.connection.get_sql_from_file('select_unscraped_urls.sql')
        sql = sql.format(shop=self.SHOP)
        df_urls = self.connection.extract_from_sql(sql)

        add_headers = {
            "Upgrade-Insecure-Requests": "1"
        }

        for _, row in df_urls.iterrows():
            pkey = row["id"]
            url = row["url"]

            now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            soup = asyncio.run(self.scrape(
                url, self.SELECTOR_SCRAPE_PRODUCT_INFO, headers=add_headers))
            df = self.transform(soup, url)

            if df is not None:
                self.load(df, temp_table)
                self.connection.update_url_scrape_status(pkey, "DONE", now)
            else:
                self.connection.update_url_scrape_status(pkey, "FAILED", now)

        for sql_file, label in [
            ('insert_into_pet_products.sql', 'data product inserted'),
            ('insert_into_pet_product_variants.sql',
             'data product variant inserted'),
            ('insert_into_pet_product_variant_prices.sql',
             'data product price inserted')
        ]:
            sql = self.connection.get_sql_from_file(
                sql_file).format(table_name=temp_table)
            self._temp_table(sql, temp_table, label)

        self._temp_table(f"DROP TABLE {temp_table};", temp_table, 'deleted')

    def get_links_by_category(self):
        temp_table = f"stg_{self.SHOP.lower()}_temp"
        self.connection.execute_query(f"DROP TABLE IF EXISTS {temp_table};")

        create_temp_sql = self.connection.get_sql_from_file(
            'create_temp_table_get_links.sql')
        create_temp_sql = create_temp_sql.format(
            table_name=temp_table)
        self._temp_table(create_temp_sql, temp_table, 'created')

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(
            BASE_DIR, 'data', 'categories', f'{self.SHOP.lower()}.json')

        with open(file_path, 'r+') as f:
            d = json.load(f)
            categories = d['data']

            for category in categories:
                df = self.extract(category)
                if df is not None:
                    self.load(df, temp_table)

        insert_url_from_temp_sql = self.connection.get_sql_from_file(
            'insert_into_urls.sql')
        insert_url_from_temp_sql = insert_url_from_temp_sql.format(
            table_name=temp_table)
        self._temp_table(insert_url_from_temp_sql, temp_table, 'data inserted')

        delete_sql = f"DROP TABLE {temp_table};"
        self._temp_table(delete_sql, temp_table, 'deleted')

    def _temp_table(self, sql, table, method):
        self.connection.execute_query(sql)
        logger.info(f"Temporary table {table} {method}.")
