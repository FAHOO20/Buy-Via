import json
import csv
import os
import time
from scraper import AmazonScraper, JarirScraper, ExtraScraper
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException


class ScraperManager:
    def __init__(self, search_values_file):
        self.search_values_file = search_values_file
        self.scrapers = [
            AmazonScraper("Amazon"),
            JarirScraper("Jarir"),
            ExtraScraper("Extra")
        ]
        self.output_file = "scraped_products.csv"

    def load_search_values(self):
        with open(self.search_values_file, 'r') as file:
            search_values_data = json.load(file)
            return search_values_data.get("search_values", [])

    def scrape_all_products(self):
        search_values = self.load_search_values()
        scraped_data = []
        product_id = 1

        for search_value in search_values:
            for scraper in self.scrapers:
                scraper.driver = scraper.setup_driver()  # Ensure driver setup for each scraper
                retries = 3
                while retries > 0:
                    try:
                        for product in scraper.scrape_products(search_value):
                            product["id"] = product_id
                            product["search_value"] = search_value
                            # Reorder dictionary keys
                            product = {
                                "id": product["id"],
                                "store": product["store"],
                                "title": product["title"],
                                "price": product["price"],
                                "info": product["info"],
                                "search_value": product["search_value"],
                                "link": product["link"],
                                "image_url": product["image_url"]
                            }
                            scraped_data.append(product)
                            print(product)  # Print each product as it is scraped
                            product_id += 1
                        break  # Exit retry loop if scraping is successful
                    except (WebDriverException, TimeoutException, NoSuchElementException) as e:
                        retries -= 1
                        print(f"Error encountered with {scraper.store_name} while scraping {search_value}: {e}. Retries left: {retries}")
                        if retries == 0:
                            print(f"Failed to scrape {scraper.store_name} for {search_value} after multiple attempts. Skipping.")
                            scraper.quit_driver()  # Quit the driver to clean up after failure
                        else:
                            time.sleep(5)  # Wait before retrying

        self.save_to_csv(scraped_data)
        for scraper in self.scrapers:
            scraper.quit_driver()  # Quit all drivers at the end

    def save_to_csv(self, data):
        csv_columns = ["id", "store", "title", "price", "info", "search_value", "link", "image_url"]
        file_exists = os.path.isfile(self.output_file)

        with open(self.output_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=csv_columns)
            if not file_exists:
                writer.writeheader()
            writer.writerows(data)

        print(f"Data saved to {self.output_file}")


if __name__ == "__main__":
    manager = ScraperManager("search_values.json")
    manager.scrape_all_products()
