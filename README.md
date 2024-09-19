# BuyVia - Product Price Comparison Tool

## Overview

**BuyVia** is a real-time product price comparison platform that scrapes multiple e-commerce websites to help users compare product prices across different stores. The project is currently in development, and it uses web scraping techniques to fetch product details such as titles, prices, and images.

## Features
- Real-time product search across multiple stores.
- Displays product details: title, price, store, and image.
- Easy-to-use interface built with **Streamlit**.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/FAHOO20/Buy-Via.git
   cd Buy-Via
2. Set up a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```
3. Make sure you have chromedriver installed and placed in the project directory.
4. Run the application:
```bash
streamlit run app.py
```

Usage
* Enter a product name (e.g., "iPhone 16") in the search bar and click Search.
* View the real-time product details scraped from supported stores.

Current Status
* Jarir store is currently supported.
* More stores will be added in future updates.
