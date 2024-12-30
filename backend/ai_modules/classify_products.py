import os
import logging
import re
import time
from tqdm import tqdm
from dotenv import load_dotenv
import openai
from models import SessionLocal, Product, Category

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Minimal logging
logging.basicConfig(level=logging.WARNING)

def get_categories(session):
    """Fetch all categories from the database and return a list of category names."""
    cats = session.query(Category).order_by(Category.category_id).all()
    return [c.category_name for c in cats]

def get_category_mappings(session):
    """Return a dict mapping category_name.lower() to category_id."""
    cats = session.query(Category).all()
    return {c.category_name.lower(): c.category_id for c in cats}

def build_few_shot_examples(categories):
    """
    Dynamically build the system message with a variety of examples.
    This should reduce the fallback usage for items like toners or inks.
    """
    examples = f"""
You must classify products into exactly one category from the following list:
{", ".join(categories)}

EXAMPLES (Product Title -> Category):
"Apple MacBook Air 13-inch" -> Laptops & Notebooks
"ASUS ROG Ally Gaming Handheld" -> Handheld Gaming Devices (ROG Ally, Steam Deck, Nintendo Switch Lite)
"Apple iPhone 15 Pro" -> Smartphones & Cell Phones
"Samsung 4K UHD Monitor" -> Monitors & Displays
"Canon EOS R5 Mirrorless Camera" -> Cameras & Camcorders
"Logitech MX Master 3 Wireless Mouse" -> Computer Peripherals (Keyboards, Mice)
"Breville Espresso Machine" -> Kitchen Appliances (Blenders, Microwaves, Coffee Makers)
"Ring Video Doorbell" -> Home Security & Surveillance
"Adidas Running Shoes" -> Shoes (Men, Women, Kids)
"Paper Mate Ballpoint Pens" -> Office Supplies (Paper, Pens, Folders)
"Nintendo Switch OLED Console" -> Gaming Consoles (PlayStation, Xbox, Nintendo)
"Zelda: Tears of the Kingdom" -> Video Games
"Dyson Vacuum Cleaner" -> Home Appliances (Refrigerators, Washers)
"PlayStation 5 Controller" -> Gaming Accessories (Controllers, VR Headsets, Cases)
"ROG Gladius III Wireless Gaming Mouse" -> Computer Peripherals (Keyboards, Mice)
"HP 203A Laser Toner Cartridge" -> Printers & Scanners
"4'x6' Thermal Shipping Labels Roll" -> Office Supplies (Paper, Pens, Folders)
"Canon Pixma G3420 MegaTank AIO" -> Printers & Scanners
"Car Dashboard Phone Mount" -> Car Electronics & Accessories (Car Stereos, Dashcams, GPS)
"GoPro Hero 11 Black" -> Cameras & Camcorders
"ASUS GeForce RTX 4070 GPU" -> Computer Components (CPUs, GPUs, etc.)

DO NOT EXPLAIN. JUST OUTPUT THE EXACT CATEGORY NAME.
    """
    return examples.strip()

def classify_product_title(title: str, categories) -> str:
    """
    Classify the product title using GPT with robust retry for rate-limit errors.
    Returns the category string (e.g., "Printers & Scanners").
    """
    few_shot = build_few_shot_examples(categories)
    user_message = f'Product title: "{title}"\nCategory:'

    while True:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # or another model you have access to
                messages=[
                    {"role": "system", "content": few_shot},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=20,
                temperature=0.0
            )
            category_candidate = response.choices[0].message.content.strip()
            break  # Classification was successful, exit loop
        except Exception as e:
            error_msg = str(e)
            print(f"Error classifying title '{title}': {error_msg}")

            # Try to parse "Please try again in XXXs" or default to 10 seconds
            match = re.search(r'Please try again in ([0-9.]+)s', error_msg)
            wait_time = float(match.group(1)) if match else 10.0
            print(f"Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)

    # Validate the returned category
    cat_lower = category_candidate.lower()
    known_categories = [c.lower() for c in categories]
    if cat_lower in known_categories:
        for cat in categories:
            if cat.lower() == cat_lower:
                return cat

    # If not recognized, fallback
    print(f"Unknown category returned: '{category_candidate}'. Using fallback.")
    return "General (Fallback category)"

def update_product_category(session, product, category_name, name_to_id):
    """
    Update a product's category. Commit and refresh so the session is in sync.
    """
    new_cat_id = name_to_id.get(category_name.lower(), 54)  # 54 is the 'General' fallback
    product.category_id = new_cat_id
    session.commit()
    session.refresh(product)  # Make sure session sees the updated category_id

def classify_products(batch_size=100, start_id=None):
    """
    Classify all products that have category_id=54 until none remain,
    starting only from product_id >= start_id if specified.

    Features:
      - Wait/retry if we hit rate-limit errors, so we never skip a product.
      - Use a local memory set so if an item is reclassified into 54 again,
        we don't keep picking it up in subsequent loops of the same run.
      - Optional 'start_id' to skip products with an ID below that value.
    """
    already_fallback_ids = set()  # Track product IDs that re-fallback to 54 in same run

    while True:
        session = SessionLocal()
        name_to_id = get_category_mappings(session)
        categories = get_categories(session)

        target_category_id = 54
        query = session.query(Product).filter(Product.category_id == target_category_id)

        # If user specified a starting ID, only classify products with ID >= that
        if start_id is not None:
            query = query.filter(Product.product_id >= start_id)

        # Exclude products that ended in fallback again from previous passes
        if already_fallback_ids:
            query = query.filter(~Product.product_id.in_(already_fallback_ids))

        if batch_size:
            query = query.limit(batch_size)

        products = query.all()
        if not products:
            print("No more products to classify.")
            session.close()
            break

        total_in_batch = len(products)
        print(f"Fetched {total_in_batch} products from category_id={target_category_id} (start_id={start_id}).")

        for i, product in enumerate(products, start=1):
            session.refresh(product)
            # If product is no longer 54, skip
            if product.category_id != 54:
                print(f"Skipping product_id={product.product_id} (no longer in category_id=54).")
                continue

            print(f"Classifying Product ID: {product.product_id} ({i}/{total_in_batch}) - Title: {product.title}")
            new_category_name = classify_product_title(product.title, categories)
            update_product_category(session, product, new_category_name, name_to_id)

            # If item reverts to fallback (54) again, add to local memory to skip next pass
            if product.category_id == 54:
                already_fallback_ids.add(product.product_id)

            print(f"[{product.product_id}/{i}/{total_in_batch}][{new_category_name}][{product.title}]")

        session.close()

    print("Classification completed.")

if __name__ == "__main__":
    # Prompt user for a starting product ID
    user_input = input("Enter the product ID to start classification from (or press Enter to start from ID=1): ")
    if user_input.strip():
        start_id = int(user_input.strip())
    else:
        start_id = None  # Means classify from ID=1 or the smallest ID

    classify_products(batch_size=100, start_id=start_id)
