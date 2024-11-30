import streamlit as st
import pandas as pd
import base64
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import re
import undetected_chromedriver as uc
from packaging.version import Version as LooseVersion


def get_chrome_options():
    """Configure Chrome options for web scraping."""
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.page_load_strategy = 'eager'

    return options


def extract_opening_time(description):
    """Extract opening time from the address description."""
    match = re.search(r'(Opens [^·]+|Open 24 hours)', description)
    return match.group(1).strip() if match else 'Not Available'


def extract_phone(description):
    """Extract phone number from the address description."""
    match = re.search(r'·\s*(\d[\d\s]+)$', description)
    return match.group(1).strip() if match else 'Not Available'


def scroll_window(driver):
    """Scroll through search results."""
    try:
        results_container = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
        )
        last_height = driver.execute_script("return arguments[0].scrollHeight;", results_container)

        while True:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", results_container)
            sleep(2)
            new_height = driver.execute_script("return arguments[0].scrollHeight;", results_container)

            if new_height == last_height:
                print("Reached the bottom of the results.")
                break
            last_height = new_height
    except Exception as e:
        st.warning(f"Scrolling error: {e}")


def scrape_data(inp):
    """Scrape Google Maps data for a given search input."""
    driver = None
    try:
        # Configure Chrome options
        options = get_chrome_options()

        # Create WebDriver instance
        driver = uc.Chrome(options=options)

        # Navigate to Google Maps
        driver.get('https://www.google.co.in/maps')
        sleep(3)

        # Find search input and submit search
        search_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, 'searchboxinput'))
        )
        search_input.send_keys(inp)
        sleep(2)

        search_button = driver.find_element(By.ID, 'searchbox-searchbutton')
        search_button.click()
        sleep(10)

        # Scroll to load results
        scroll_window(driver)

        # Find search result items
        table = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.Nv2PK'))
        )

        data = []
        for tab in table:
            try:
                gmap = tab.find_element(By.TAG_NAME, 'a').get_attribute('href')
            except Exception:
                gmap = 'NA'

            try:
                name = tab.find_element(By.CSS_SELECTOR, 'div.qBF1Pd.fontHeadlineSmall').text
            except Exception:
                name = 'NA'

            try:
                rating_text = tab.find_element(By.CSS_SELECTOR, 'span.ZkP5Je').get_attribute('aria-label')
            except Exception:
                rating_text = 'NA'

            try:
                description = tab.find_elements(By.CSS_SELECTOR, 'div.W4Efsd')[1].text
            except Exception:
                description = 'NA'

            try:
                website = tab.find_element(By.CSS_SELECTOR, 'a.lcr4fd.S9kvJb').get_attribute('href')
            except Exception:
                website = 'NA'

            try:
                opening_time = extract_opening_time(description)
                phone_number = extract_phone(description)
                cleaned_address = re.sub(r'(Opens [^·]+|Open 24 hours|·\s*\d[\d\s]+)$', '',
                                         description).strip() or 'Not Available'

                data.append({
                    'Name': name,
                    'Address': cleaned_address,
                    'Rating': rating_text,
                    'Opening Time': opening_time,
                    'Phone Number': phone_number,
                    'Google Maps Link': gmap,
                    'Website': website
                })
            except Exception as item_error:
                print(f"Error processing item: {item_error}")
                # If there's an error in processing the item, we'll skip it and continue with the next one

        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"Scraping error: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error

    finally:
        # Ensure driver is closed
        if driver:
            driver.quit()


def get_download_link(df):
    """Create a download link for the DataFrame."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="google_maps_data.csv">Download CSV File</a>'
    return href


def main():
    st.set_page_config(page_title="Google Maps Scraper", page_icon=":mag:", layout="centered")

    # Custom CSS
    st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stTextInput > div > div > input {
        border: 2px solid #4CAF50;
        border-radius: 10px;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border-radius: 10px;
    }
    .stDataFrame {
        max-height: 400px;
        overflow: auto;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🗺️ Google Maps Business Scraper")
    st.write("Enter a search query to scrape business details from Google Maps")

    # Search input
    search_query = st.text_input("Enter Search Query", placeholder="e.g., Car service center in palakkad")

    if st.button("Scrape Data"):
        if search_query:
            with st.spinner('Scraping data...'):
                try:
                    # Scrape data
                    df = scrape_data(search_query)

                    if not df.empty:
                        # Display DataFrame
                        st.dataframe(df)

                        # Download link
                        st.markdown(get_download_link(df), unsafe_allow_html=True)
                    else:
                        st.warning("No data could be scraped. Please try a different search query.")

                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
        else:
            st.warning("Please enter a search query")


if __name__ == "__main__":
    main()
