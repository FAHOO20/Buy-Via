# Buy Via - Web Scraper for Product Comparison

## Project Overview

This project is a web scraping tool that allows users to extract product details such as prices, links, and images from the Jarir Bookstore website. It utilizes Selenium to automate the browser and scrape the data. 

The purpose is to help users compare product prices and find the best deals available on the Jarir website.

---

## Requirements

- Python 3.x
- Google Chrome Browser
- ChromeDriver (version must match the Chrome version installed)
- Selenium

---

## Installation and Setup

### 1. Clone the Repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/FAHOO20/Buy-Via.git
cd Buy-Via
```

### 2. Create a Virtual Environment (Optional but Recommended)

It is recommended to use a Python virtual environment to manage dependencies.

For Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

For Linux/Mac:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install the Requirements

Install all required Python packages:

```bash
pip install -r requirements.txt
```

---

## Chrome and ChromeDriver Setup

### Windows Setup
The project already includes `chromedriver.exe`, so there is no need to install ChromeDriver separately. Just ensure your Google Chrome browser is up-to-date and matches the ChromeDriver version.

### Linux Setup

If you are running this project on a Linux machine, follow these steps to install Google Chrome and ChromeDriver:

#### Install Google Chrome:
1. Download and install Google Chrome based on your Linux distribution:

   For Ubuntu/Debian:
   ```bash
   wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
   sudo dpkg -i google-chrome-stable_current_amd64.deb
   sudo apt-get install -f
   ```

2. Verify the installation:
   ```bash
   google-chrome --version
   ```

#### Download and Setup ChromeDriver:

1. Download the correct version of ChromeDriver that matches your Google Chrome version. You can check your Chrome version by running:
   
   ```bash
   google-chrome --version
   ```

2. Visit the [ChromeDriver Downloads](https://sites.google.com/a/chromium.org/chromedriver/downloads) page and download the ChromeDriver version matching your Chrome version.

3. Unzip the ChromeDriver and move it to your project folder:

   ```bash
   wget https://chromedriver.storage.googleapis.com/115.0.5790.102/chromedriver_linux64.zip
   unzip chromedriver_linux64.zip
   mv chromedriver chromedriver_linux
   ```

4. Update your Python script to use the Linux version of ChromeDriver by modifying the driver path in `jarir_scraper.py`:
   ```python
   chrome_driver_path = os.path.join(os.path.dirname(__file__), "chromedriver_linux")
   ```

---

## Running the Project

1. **Run the Web Scraper using Streamlit**:
   The `app.py` file provides a Streamlit interface for the scraper.

   Run it by executing:
   ```bash
   streamlit run app.py
   ```

2. **Scraping from Command Line**:
   You can run the scraper directly from the command line by using `jarir_scraper.py`:

   ```bash
   python jarir_scraper.py
   ```

   You will be prompted to enter a search term, and the scraper will display product details in the console.

---

## Troubleshooting

- **ChromeDriver Version Issues**: Ensure that the version of ChromeDriver matches your Google Chrome version. If there's a version mismatch, the scraper will not work.
  
- **Virtual Environment**: If you encounter package conflicts or Python-related issues, consider using a virtual environment as mentioned above.

---
