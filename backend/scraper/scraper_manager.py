# backend/scraper/scraper_manager.py
from scraper.scraper import AmazonScraper, JarirScraper, ExtraScraper
from models import Store, Product, Category, ProductPriceHistory, engine
from sqlalchemy.orm import Session
import json
import time
from datetime import datetime, timezone
import random
import os
from concurrent.futures import ThreadPoolExecutor

class ScraperManager:
    def __init__(self, search_values_file="scraper/search_values.json"):
        self.search_values_file = os.path.join(
            os.path.dirname(__file__), search_values_file
        )
        self.scrapers = [
            AmazonScraper("Amazon"),
            JarirScraper("Jarir"),
            ExtraScraper("Extra"),
        ]

    def load_search_values(self):
        """Load search values from a JSON file and shuffle them."""
        with open(self.search_values_file, 'r') as file:
            search_values_data = json.load(file)
            search_values = search_values_data.get("search_values", [])
            random.shuffle(search_values)  # Shuffle the search values
            return search_values

    def store_to_database(self, db: Session, data: dict):
        """Store a scraped product in the database and log actions."""
        try:
            price = float(data["price"])
        except (ValueError, TypeError):
            price = None  # Set to None if price is "N/A" or invalid

        info = data.get("info")
        if info == "N/A" or not info:
            info = None

        store_name = data["store"]
        title = data["title"]
        search_value = data["search_value"]
        link = data["link"]
        image_url = data["image_url"]

        # Check if store exists; if not, create it
        store = db.query(Store).filter_by(store_name=store_name).first()
        if not store:
            store = Store(store_name=store_name)
            db.add(store)
            db.commit()
            db.refresh(store)

        # Check if category exists; if not, create it
        category_name = "General"  # Default category
        category = db.query(Category).filter_by(category_name=category_name).first()
        if not category:
            category = Category(category_name=category_name)
            db.add(category)
            db.commit()
            db.refresh(category)

        # Check if the product already exists in the same store
        existing_product = db.query(Product).filter_by(
            title=title, store_id=store.store_id
        ).first()

        if existing_product:
            updated = False
            messages = []

            # If price has changed
            if existing_product.price != price:
                # Record price history
                price_history = ProductPriceHistory(
                    product_id=existing_product.product_id,
                    old_price=existing_product.price if existing_product.price is not None else 0.0,
                    new_price=price if price is not None else 0.0,
                    change_date=datetime.now(timezone.utc)
                )
                db.add(price_history)

                messages.append(f"Price updated from {existing_product.price} to {price}")
                existing_product.price = price
                updated = True

            # Update link if changed
            if existing_product.link != link:
                messages.append("Link updated")
                existing_product.link = link
                updated = True

            # Update image_url if changed
            if existing_product.image_url != image_url:
                messages.append("Image URL updated")
                existing_product.image_url = image_url
                updated = True

            # If any updates have occurred
            if updated:
                if existing_product.search_value != search_value:
                    messages.append(f"Search value updated to {search_value}")
                    existing_product.search_value = search_value

                existing_product.last_updated = datetime.now(timezone.utc)
                print(f"[{store_name}] Product updated in the database: '{title}'")
                for msg in messages:
                    print(f" - {msg}")
            else:
                print(f"[{store_name}] Product skipped (no changes): '{title}'")
        else:
            # Create new product
            new_product = Product(
                title=title,
                price=price,
                info=info,
                search_value=search_value,
                link=link,
                image_url=image_url,
                availability=True,
                store_id=store.store_id,
                category_id=category.category_id,
            )
            db.add(new_product)
            print(f"[{store_name}] Product '{title}' added to the database.")

        # Commit changes to the database
        db.commit()


    def run_scraper_for_value(self, scraper, search_value):
        """Run a single scraper for a given search value in a separate thread."""
        with Session(engine) as db:
            print(f"Using scraper: {scraper.store_name}")
            retries = 3
            while retries > 0:
                try:
                    # Ensure driver is set up
                    if not scraper.driver:
                        scraper.driver = scraper.setup_driver()
                    for product in scraper.scrape_products(search_value):
                        product_data = {
                            "store": product["store"],
                            "title": product["title"],
                            "price": product["price"],
                            "info": product["info"],
                            "search_value": search_value,
                            "link": product["link"],
                            "image_url": product["image_url"],
                        }
                        self.store_to_database(db, product_data)
                    break  # Exit retry loop if scraping is successful
                except Exception as e:
                    retries -= 1
                    print(
                        f"Error with {scraper.store_name} while scraping '{search_value}': {e}. Retries left: {retries}"
                    )
                    scraper.quit_driver()  # Quit the driver to reset state
                    if retries == 0:
                        print(
                            f"Failed to scrape {scraper.store_name} for '{search_value}' after multiple attempts. Skipping."
                        )
                    else:
                        time.sleep(5)  # Wait before retrying

            # Quit the scraper's driver after scraping
            scraper.quit_driver()

    def scrape_all_products(self):
        """Scrape products and store them in the database simultaneously for each store."""
        search_values = self.load_search_values()

        for search_value in search_values:
            print(f"\nStarting scraping for search value: '{search_value}'")

            # Run each store scraper in parallel
            with ThreadPoolExecutor(max_workers=len(self.scrapers)) as executor:
                futures = []
                for scraper in self.scrapers:
                    futures.append(executor.submit(self.run_scraper_for_value, scraper, search_value))

                # Wait for all threads to finish
                for future in futures:
                    future.result()

if __name__ == "__main__":
    manager = ScraperManager("search_values.json")
    manager.scrape_all_products()
