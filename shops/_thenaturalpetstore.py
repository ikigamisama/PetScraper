from functions.etl import PetProductsETL


class TheNaturalPetStoreETL(PetProductsETL):
    def __init__(self):
        super().__init__()
        self.SHOP = "TheNaturalPetStore"
        self.BASE_URL = "https://www.thenaturalpetstore.co.uk"
        self.SELECTOR_SCRAPE_PRODUCT_INFO = ''

    def extract(self):
        print(f"[{self.SHOP}] Extracting data from categories...")

    def transform(self):
        print(f"[{self.SHOP}] Transforming data...")
