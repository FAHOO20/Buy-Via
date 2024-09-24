from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, WebDriverException
from time import sleep
import urllib.parse
import os

def setup_driver():
    """Sets up the Selenium WebDriver with options to avoid detection as a bot."""
    chrome_driver_path = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
  # Update with your ChromeDriver path
    service = Service(executable_path=chrome_driver_path)
    options = webdriver.ChromeOptions()
    
    # Add a user-agent to prevent detection as a bot
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Disable automation-related switches
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Enable headless mode
    options.add_argument("--headless")  
    options.add_argument("--window-size=1920x1080")

    # Optional: block images and unnecessary resources
    options.add_argument("--disable-images")  # Disable images (if you don't care about them)
    options.add_argument("--blink-settings=imagesEnabled=false")

    # Create the WebDriver instance
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def handle_popups(driver):
    """Handles popups like language selection and cookie consent."""
    try:
        # Wait for the language popup and select the language
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button#switcher-button-en"))).click()
        print("Language selected: English")
    except TimeoutException:
        print("Language popup did not appear or was already handled.")

    try:
        # Accept cookie consent if the consent popup appears
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
        print("Accepted cookie consent.")
    except TimeoutException:
        print("Cookie consent popup did not appear or was already handled.")

def scrape_jarir(search_value, max_scrolls=3, retries=2, retry_delay=5):
    """
    Scrape products from the Jarir website based on the search value.
    
    :param search_value: The search query for the products.
    :param max_scrolls: The maximum number of times to scroll down to load new products.
    :param retries: The number of times to retry if the page fails to load.
    :param retry_delay: The delay between retries.
    :yield: Product details one at a time, ensuring no duplication.
    """
    driver = setup_driver()

    # URL encode the search query to handle non-English characters
    encoded_search_value = urllib.parse.quote(search_value)
    url = f"https://www.jarir.com/sa-en/catalogsearch/result?search={encoded_search_value}"
    
    attempt = 0
    while attempt < retries:
        try:
            print(f"Attempt {attempt + 1} to open URL: {url}")
            driver.get(url)
            
            # Handle popups
            handle_popups(driver)

            # Wait for the first product tile to appear
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CLASS_NAME, "product-tile")))
            
            print("Page loaded successfully.")
            break  # If no exception occurred, break out of the retry loop

        except (TimeoutException, WebDriverException) as e:
            print(f"Error opening page (Attempt {attempt + 1}): {e}")
            attempt += 1
            if attempt < retries:
                print(f"Retrying in {retry_delay} seconds...")
                sleep(retry_delay)
            else:
                print("Failed to load the page after several attempts. Exiting.")
                driver.quit()
                return  # Exit if all retry attempts fail

    # Maintain a set of unique product identifiers to prevent duplication
    unique_products = set()

    def extract_products():
        """
        Extract product details from the currently visible products on the page.
        Yields product data if it's not a duplicate.
        """
        try:
            product_elements = driver.find_elements(By.CLASS_NAME, "product-tile")
            for product in product_elements:
                try:
                    # Extract product title and link
                    title = product.find_element(By.CLASS_NAME, "product-title__title").text
                    link = product.find_element(By.CSS_SELECTOR, "a.product-tile__link").get_attribute("href")
                    
                    # Try to extract price
                    try:
                        price = product.find_element(By.CLASS_NAME, "price").text
                    except Exception:
                        price = "N/A"
                    
                    # Try to extract additional info
                    try:
                        info = product.find_element(By.CLASS_NAME, "product-title__info").text.strip()
                    except Exception:
                        info = "No additional info available"
                    
                    # Get product image URL (avoid placeholders)
                    try:
                        image_elements = product.find_elements(By.CSS_SELECTOR, "img.image--contain")
                        image_url = next((img.get_attribute("src") for img in image_elements if 'placeholder' not in img.get_attribute("src")), "")
                    except Exception:
                        image_url = "Image not available"

                    # Create a unique identifier tuple (title, link) for deduplication
                    product_key = (title, link)
                    
                    # Ensure the product is unique by checking against the set
                    if product_key not in unique_products:
                        unique_products.add(product_key)
                        # Yield product details one at a time
                        yield {
                            "store": "Jarir Bookstore",
                            "title": title,
                            "link": link,
                            "price": price,
                            "info": info,
                            "image_url": image_url
                        }

                except StaleElementReferenceException:
                    print(f"Stale element error encountered, skipping product")
                    continue  # Skip the stale product element

        except Exception as e:
            print(f"Error extracting product: {e}")

    yield from extract_products()  # Yield products found on initial load

    # Infinite scroll to load more products
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scrolls):
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(1.5)  # Reduce sleep time to speed up the scrolling
            yield from extract_products()  # Yield newly loaded products
            
            # Check if the page height has changed to determine if more products were loaded
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("No more products to load.")
                break  # Stop scrolling if no new products are loaded
            last_height = new_height
        except StaleElementReferenceException:
            print("Encountered stale element reference during scroll, trying again.")
            sleep(1)  # Wait before retrying
        except Exception as scroll_error:
            print(f"Error while scrolling: {scroll_error}")
            break

    driver.quit()

# Example usage to test without Streamlit
if __name__ == "__main__":
    search_value = input("Enter the search value: ")
    
    for product in scrape_jarir(search_value):
        print(f"Product: {product['title']}")
        print(f"Price: {product['price']}")
        print(f"Info: {product['info']}")
        print(f"Image URL: {product['image_url']}")
        print(f"Link: {product['link']}")
        print("-" * 50)
