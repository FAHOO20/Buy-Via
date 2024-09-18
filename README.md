# Buy-Via Platform

**Buy-Via** is a platform designed to help users compare product prices from multiple e-commerce websites. By integrating web scraping, API access, and machine learning, Buy-Via ensures users can find the best deals available online. This project includes a web scraper for Jarir Bookstore, which can be extended to include other stores.

## Project Objective

Buy-Via addresses the problem of price dispersion in online retail by providing users with a comprehensive tool to compare product prices. It ensures that users can:
- Access real-time product prices.
- Get personalized recommendations.
- Receive price drop alerts via email.

## Installation

### Prerequisites

- Python 3.x installed on your machine.
- Chrome browser installed.
- ChromeDriver placed in your project folder (or specified path).

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/FAHOO20/Buy-Via.git
   cd Buy-Via
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - **Windows**:
     ```bash
     venv\Scripts\activate
     ```
   - **Linux/Mac**:
     ```bash
     source venv/bin/activate
     ```

4. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Add ChromeDriver**:
   - Place the `chromedriver.exe` file in the project folder.
   - Update the path in the code if necessary:
     ```python
     chrome_driver_path = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
     ```

### Running the Web Scraper

1. Activate the virtual environment (if not already activated).
2. Run the script:
   ```bash
   python jarir_scraper.py
   ```

3. Enter a search term when prompted (e.g., "iPhone 16"), and the scraper will fetch and display product information from Jarir Bookstore.

### Using Streamlit Web Interface

1. Install **Streamlit** (if not already installed):
   ```bash
   pip install streamlit
   ```

2. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

3. Open your browser to the URL provided by Streamlit (typically `http://localhost:8501`) to interact with the scraping tool via a web interface.

## Usage Instructions

### Windows
1. Follow the steps above to set up the virtual environment and run the scraper or the web app using Streamlit.
2. Ensure that ChromeDriver is placed in the correct folder and Chrome is installed.

### Linux
1. Install Chrome and ChromeDriver on your Linux machine.
2. Ensure the path to the ChromeDriver is correctly specified in the project folder.
3. Follow the same steps for setting up and running the scraper as outlined above.

## Contributing

Feel free to open an issue or a pull request if you'd like to contribute. Make sure to follow best practices for Python and adhere to the project's coding style.

## License

This project is licensed under the MIT License.
```

### To use this:

1. Create a new file in your project directory called `README.md`.
2. Copy the content from above and paste it into the `README.md` file.
3. Commit the changes and push to your GitHub repository.

```bash
git add README.md
git commit -m "Added project README"
git push origin master
```
