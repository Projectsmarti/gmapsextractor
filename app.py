import streamlit as st
import pandas as pd
import base64
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from time import sleep
import re


def get_chrome_options():
    """Configure Chrome options for web scraping."""
    options = ChromeOptions()
    options.add_argument("--start-maximized")
    options.page_load_strategy = 'eager'
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2
        }
    )
    return options


def extract_opening_time(description):
    """Extract opening time from the address description."""
    match = re.search(r'(Opens [^·]+|Open 24 hours)', description)
    return match.group(1).strip() if match else None


def extract_phone(description):
    """Extract phone number from the address description."""
    match = re.search(r'·\s*(\d[\d\s]+)$', description)
    return match.group(1).strip() if match else None


def scroll_window(driver):
    """Scroll through search results."""
    results_container = driver.find_element(By.XPATH, "//div[@role='feed']")
    last_height = driver.execute_script("return arguments[0].scrollHeight;", results_container)

    while True:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", results_container)
        sleep(2)
        new_height = driver.execute_script("return arguments[0].scrollHeight;", results_container)
        if new_height == last_height:
            break
        last_height = new_height


def scrape_data(inp):
    """Scrape Google Maps data for a given search input."""
    options = get_chrome_options()
    driver = webdriver.Chrome(options=options)

    try:
        driver.get('https://www.google.co.in/maps/@11.0139467,76.9672346')
        sleep(3)
        driver.find_element(By.ID, 'searchboxinput').send_keys(inp)
        sleep(3)
        driver.find_element(By.ID, 'searchbox-searchbutton').click()
        sleep(10)

        scroll_window(driver)

        table = driver.find_element(By.CSS_SELECTOR, 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde.ecceSd').find_elements(
            By.CSS_SELECTOR, '.Nv2PK')

        data = []
        for tab in table:
            try:
                gmap = tab.find_element(By.TAG_NAME, 'a').get_attribute('href')
            except:
                gmap = 'NA'
            try:
                name = tab.find_element(By.CSS_SELECTOR, 'div.qBF1Pd.fontHeadlineSmall').text
            except:
                name = 'NA'
            try:
                rating_text = tab.find_element(By.CSS_SELECTOR, 'span.ZkP5Je').get_attribute('aria-label')
            except:
                rating_text = 'NA'
            try:
                description = tab.find_elements(By.CSS_SELECTOR, 'div.W4Efsd')[1].text
            except:
                description = 'NA'
            try:
                website = tab.find_element(By.CSS_SELECTOR, 'a.lcr4fd.S9kvJb').get_attribute('href')
            except:
                website = 'NA'

            opening_time = extract_opening_time(description)
            phone_number = extract_phone(description)
            cleaned_address = re.sub(r'(Opens [^·]+|Open 24 hours|·\s*\d[\d\s]+)$', '', description).strip()

            data.append({
                'GMAP': gmap,
                'Name': name,
                'Rating_text': rating_text,
                'Address': cleaned_address,
                'Opening Time': opening_time,
                'Phone Number': phone_number,
                'Website': website
            })

        df = pd.DataFrame(data)
        df = df[['Name', 'Address', 'Rating_text', 'Opening Time', 'Phone Number', 'GMAP', 'Website']]

        return df

    finally:
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

                    # Display DataFrame
                    st.dataframe(df)

                    # Download link
                    st.markdown(get_download_link(df), unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.warning("Please enter a search query")


if __name__ == "__main__":
    main()