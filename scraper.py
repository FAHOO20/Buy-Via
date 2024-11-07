# scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from time import sleep
import urllib.parse
import platform
import os
import stat

class StoreScraper:
    def __init__(self, store_name):
        self.store_name = store_name
        self.driver = self.setup_driver()

    def setup_driver(self):
        project_dir = os.path.dirname(os.path.abspath(__file__))

        # Define the path to chromedriver within the project directory
        if platform.system() == "Linux":
            driver_path = os.path.join(project_dir, "chromedriver")
        elif platform.system() == "Windows":
            driver_path = os.path.join(project_dir, "chromedriver.exe")
        else:
            raise Exception("Unsupported OS. This script supports only Windows and Linux.")

        # Ensure the chromedriver has executable permissions (only needed for Linux)
        if platform.system() == "Linux" and not os.access(driver_path, os.X_OK):
            os.chmod(driver_path, stat.S_IEXEC)

        # Set up the Chrome service with the specified path
        service = Service(executable_path=driver_path)

        # Set up Chrome options
        options = webdriver.ChromeOptions()
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--allow-insecure-localhost")
        options.add_argument("--headless")  # Ensure this line is present for headless mode

        # Initialize the Chrome WebDriver with the specified service and options
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def quit_driver(self):
        if self.driver:
            self.driver.quit()

    def clean_image_url(self, image_url):
        if image_url.startswith("//"):
            image_url = "https:" + image_url

        image_url = image_url.replace("////", "//")

        if "100_00" in image_url:
            image_url = image_url.replace("100_00", "100_01")

        if "?locale=" in image_url:
            image_url = image_url.split("?locale=")[0] + "?locale=en-GB,en-"
        elif "&amp;fmt=" in image_url:
            image_url = image_url.split("&amp;")[0]

        return image_url

class AmazonScraper(StoreScraper):
    def scrape_products(self, search_value, max_pages=5):
        encoded_search_value = urllib.parse.quote(search_value)
        base_url = f"https://www.amazon.sa/s?k={encoded_search_value}&language=en_AE"

        try:
            for page in range(1, max_pages + 1):
                url = f"{base_url}&page={page}"
                print(f"Loading page {page} for Amazon - URL: {url}")
                try:
                    self.driver.get(url)
                except TimeoutException:
                    print(f"Connection timed out when loading {url}. Retrying...")
                    continue

                # Wait for the page to load and display product results
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-main-slot"))
                )
                print(f"Scraping results from {self.store_name} - Page {page} for: {search_value}")

                unique_products = set()

                def extract_products():
                    product_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.s-result-item[data-component-type='s-search-result']")
                    for product in product_elements:
                        try:
                            # Extract the product title
                            title_elem = product.find_element(By.CSS_SELECTOR, "h2 .a-link-normal")
                            title = title_elem.text

                            # Extract the product link
                            link = title_elem.get_attribute("href")

                            # Extract the product price
                            try:
                                price_whole = product.find_element(By.CSS_SELECTOR, "span.a-price-whole").text
                                price_fraction = product.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text
                                price = f"SAR {price_whole}.{price_fraction}"
                            except NoSuchElementException:
                                price = "N/A"

                            # Extract the product image URL
                            try:
                                image_url = product.find_element(By.CSS_SELECTOR, "img.s-image").get_attribute("src")
                            except NoSuchElementException:
                                image_url = "https://via.placeholder.com/150"

                            product_key = (title, link)
                            if product_key not in unique_products:
                                unique_products.add(product_key)
                                yield {
                                    "store": self.store_name,
                                    "title": title,
                                    "link": link,
                                    "price": price,
                                    "info": "N/A",  # Placeholder for additional product info
                                    "image_url": image_url
                                }
                        except (NoSuchElementException, WebDriverException) as e:
                            print(f"Skipping product due to an error: {e}")

                yield from extract_products()

                # Check for the presence of a "Next" button to continue pagination
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "a.s-pagination-next")
                    if not next_button.is_enabled():
                        print("No more pages to load.")
                        break
                except NoSuchElementException:
                    print("No 'Next' button found. Stopping pagination.")
                    break

        except (TimeoutException, WebDriverException) as e:
            print(f"Error during scraping: {e}")
        finally:
            self.quit_driver()

# Jarir-specific scraper class inheriting from StoreScraper
class JarirScraper(StoreScraper):
    def handle_popups(self):
        # Handle language popup
        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button#switcher-button-en"))
            ).click()
            print("Language selected: English")
        except TimeoutException:
            print("Language popup did not appear or was already handled.")
        
        # Handle cookie consent popup
        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
            print("Accepted cookie consent.")
        except TimeoutException:
            print("Cookie consent popup did not appear or was already handled.")

    def scrape_products(self, search_value, max_scrolls=5):
        encoded_search_value = urllib.parse.quote(search_value)
        url = f"https://www.jarir.com/sa-en/catalogsearch/result?search={encoded_search_value}"

        try:
            self.driver.get(url)
            self.handle_popups()

            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product-tile"))
            )
            print(f"Scraping results from {self.store_name} for: {search_value}")

            unique_products = set()

            def extract_products():
                product_elements = self.driver.find_elements(By.CLASS_NAME, "product-tile")
                for product in product_elements:
                    title = product.find_element(By.CLASS_NAME, "product-title__title").text
                    link = product.find_element(By.CSS_SELECTOR, "a.product-tile__link").get_attribute("href")
                    price = product.find_element(By.CLASS_NAME, "price").text if product.find_elements(By.CLASS_NAME, "price") else "N/A"
                    info = product.find_element(By.CLASS_NAME, "product-title__info").text.strip() if product.find_elements(By.CLASS_NAME, "product-title__info") else "No additional info available"
                    image_url = next((img.get_attribute("src") for img in product.find_elements(By.CSS_SELECTOR, "img.image--contain") if 'placeholder' not in img.get_attribute("src")), "")

                    product_key = (title, link)
                    if product_key not in unique_products:
                        unique_products.add(product_key)
                        yield {
                            "store": self.store_name,
                            "title": title,
                            "link": link,
                            "price": price,
                            "info": info,
                            "image_url": image_url
                        }

            yield from extract_products()

            last_height = self.driver.execute_script("return document.body.scrollHeight")
            for _ in range(max_scrolls):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                sleep(3)
                yield from extract_products()

                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print("No more products to load.")
                    break
                last_height = new_height

        except (TimeoutException, WebDriverException) as e:
            print(f"Error during scraping: {e}")
        finally:
            self.quit_driver()

# Extra-specific scraper class inheriting from StoreScraper
class ExtraScraper(StoreScraper):
    def scrape_products(self, search_value, max_pages=5):
        # Encode the search value for URL usage
        encoded_search_value = urllib.parse.quote(search_value)
        base_url = f"https://www.extra.com/en-sa/search/?q={encoded_search_value}%3Arelevance%3Atype%3APRODUCT&text={encoded_search_value}&pageSize=96&sort=relevance"

        unique_products = set()

        try:
            for page in range(1, max_pages + 1):
                # Construct the URL for each page using the correct format
                url = f"{base_url}&pg={page}"
                print(f"Loading page {page} for Extra - URL: {url}")

                # Navigate to the URL
                self.driver.get(url)

                # Wait for the product tiles to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "product-tile-wrapper"))
                    )
                    print(f"Scraping results from {self.store_name} - Page {page} for: {search_value}")

                    # Extract products on the current page
                    def extract_products():
                        product_elements = self.driver.find_elements(By.CLASS_NAME, "product-tile-wrapper")
                        for product in product_elements:
                            try:
                                # Extract product details
                                title = product.find_element(By.CLASS_NAME, "product-name-data").text
                                link = product.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                                price = product.find_element(By.CLASS_NAME, "price").text.replace("SAR", "").strip()
                                info = "; ".join([li.text for li in product.find_elements(By.CSS_SELECTOR, "ul.product-stats li")])
                                image_url = product.find_element(By.CSS_SELECTOR, "picture img").get_attribute("src")

                                # Clean the image URL
                                image_url = self.clean_image_url(image_url)

                                # Use a fallback image if the URL is invalid
                                if not image_url or image_url == "0":
                                    image_url = "https://via.placeholder.com/150"

                                product_key = (title, link)
                                if product_key not in unique_products:
                                    unique_products.add(product_key)
                                    yield {
                                        "store": self.store_name,
                                        "title": title,
                                        "link": link,
                                        "price": price,
                                        "info": info,
                                        "image_url": image_url
                                    }
                            except (NoSuchElementException, WebDriverException) as e:
                                print(f"Skipping product due to an error: {e}")

                    yield from extract_products()

                    # Check if the current page is the last page
                    pagination_element = self.driver.find_elements(By.CLASS_NAME, "pagination-wrapper")
                    if pagination_element:
                        next_button = self.driver.find_elements(By.CSS_SELECTOR, "li.next")
                        if not next_button or 'hidden' in next_button[0].get_attribute('class'):
                            print("No more pages to load. Stopping pagination.")
                            break
                    else:
                        print("No pagination found. Assuming this is the only page.")
                        break

                except TimeoutException:
                    print(f"Timeout loading page {page} for Extra. Retrying...")
                except WebDriverException as e:
                    print(f"WebDriverException on page {page}: {e}. Skipping this page.")
                except Exception as e:
                    print(f"Unexpected error on page {page}: {e}. Skipping this page.")
                
        except (TimeoutException, WebDriverException) as e:
            print(f"Error during scraping: {e}")
        finally:
            self.quit_driver()
