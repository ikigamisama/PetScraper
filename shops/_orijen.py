from functions.etl import PetProductsETL


class OrijenETL(PetProductsETL):
    def __init__(self):
        super().__init__()
        self.SHOP = "Orijen"
        self.BASE_URL = "https://www.orijenpetfoods.co.uk"
        self.SELECTOR_SCRAPE_PRODUCT_INFO = ''

    def extract(self):
        print(f"[{self.SHOP}] Extracting data from categories...")

    def transform(self):
        print(f"[{self.SHOP}] Transforming data...")
