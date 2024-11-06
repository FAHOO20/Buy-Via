import streamlit as st
import time
from pathlib import Path
from scraper import ScraperManager

# Title and instructions
st.title("Real-Time Product Scraper")
st.write("Enter a search term and see products as they are scraped from online stores!")

# User input for search term
search_term = st.text_input("Search for products", "iPhone 16")

# Search button to trigger the scraping process
if st.button("Search"):
    if search_term:
        st.write(f"Searching for: {search_term}")
        
        # Create an instance of the ScraperManager class from store_scraper.py
        scraper_manager = ScraperManager()
        progress_text = st.empty()  # Placeholder for progress text
        product_display = st.empty()  # Container to display products

        product_count = 0
        products_fetched = []

        try:
            # Real-time scraping logic
            for product in scraper_manager.scrape_all_stores(search_term):
                product_count += 1
                products_fetched.append(product)

                # Update progress
                progress_text.text(f"Scraped {product_count} products so far...")

                # Dynamically update the product display
                with product_display.container():
                    for p in products_fetched:
                        st.write(f"### {p['title']}")
                        st.write(f"**Price**: {p['price']}")
                        st.write(f"**Store**: {p['store']}")
                        st.write(f"**Info**: {p['info']}")
                        if p['image_url']:
                            st.image(p['image_url'], width=150)
                        st.write(f"[Product Link]({p['link']})")
                        st.write("---")

                # Add a small delay to simulate real-time fetching
                time.sleep(1)
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a search term.")
