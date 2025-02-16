#!/usr/bin/env python3
"""
historical_vital_records_downloader.py --- A modular Selenium-based scraper
for downloading PDF files from historical vital records websites.
Version: 1.1.7

This script now allows easy configuration for borough (county), certificate type,
and year range. Modify the BOROUGH, CERT_TYPE, START_YEAR, and END_YEAR at the top of
the file as needed, and the BASE_URL will adjust automatically.
"""

import os
import time
import logging
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from global_updater import update_global_file

# -----------------------------
# Configuration
# -----------------------------
MAX_FILES = None  # Set to 1, 50, or 0/None for no limit
CERTIFICATES_PER_PAGE = None  # Positive int for limit; 0/None => process all
MAX_PAGES = 12  # 0/None for no limit

BOROUGH = "manhattan"   # e.g., "manhattan", "kings", "queens", "bronx", "richmond"
START_YEAR = 1865
END_YEAR = 1867
CERT_TYPE = "death"     # "birth", "death", or "marriage"

BASE_URL_TEMPLATE = (
    "https://a860-historicalvitalrecords.nyc.gov/browse-all?"
    "year=&number=&last_name=&first_name=&page=&certificate_type={cert_type}&"
    "year_range={start_year}+to+{end_year}&county={borough}"
)
BASE_URL = BASE_URL_TEMPLATE.format(
    cert_type=CERT_TYPE,
    start_year=START_YEAR,
    end_year=END_YEAR,
    borough=BOROUGH
)

RECORDS_FILE = './records/saved_files.json'


def load_records():
    os.makedirs(os.path.dirname(RECORDS_FILE), exist_ok=True)
    if os.path.exists(RECORDS_FILE):
        with open(RECORDS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_record(record):
    records = load_records()
    records.append(record)
    with open(RECORDS_FILE, 'w') as f:
        json.dump(records, f, indent=4)

    # Immediately update global file using rename_key="output filename"
    update_global_file(RECORDS_FILE, rename_key="output filename")


def already_downloaded(file_name):
    records = load_records()
    return any(record.get("output filename") == file_name for record in records)


# Plugin registry for scraper modules
SCRAPER_PLUGINS = {}


def register_scraper(name):
    """
    Decorator to register a scraper plugin.
    """
    def decorator(cls):
        SCRAPER_PLUGINS[name] = cls
        return cls
    return decorator


class BaseScraper:
    """
    BaseScraper is an abstract class defining the interface for all scraper plugins.
    """
    def __init__(self, download_dir='downloads', driver_path=None):
        self.download_dir = os.path.abspath(download_dir)
        os.makedirs(self.download_dir, exist_ok=True)
        self.driver = None
        self.wait = None
        self.driver_path = driver_path
        self.download_count = 0
        self.setup_driver()

    def setup_driver(self):
        raise NotImplementedError("setup_driver must be implemented by subclasses.")

    def scrape(self):
        raise NotImplementedError("scrape must be implemented by subclasses.")

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logging.info(f"Driver quit encountered an error: {e}")


@register_scraper("nyc_death_certificate")
class NYCDeathCertificateScraper(BaseScraper):
    """
    NYCDeathCertificateScraper scrapes the NYC historical vital records website
    to download certificate PDFs (default is death, but can be changed).
    """
    def setup_driver(self):
        chrome_options = Options()
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        if self.driver_path:
            service = Service(self.driver_path)
        else:
            service = Service("chromedriver")
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def wait_for_downloads_complete(self, timeout=60):
        elapsed = 0
        while elapsed < timeout:
            if not any(fname.endswith(".crdownload") for fname in os.listdir(self.download_dir)):
                logging.info("Download complete.")
                return True
            time.sleep(1)
            elapsed += 1
        logging.warning("Download did not complete within the timeout period.")
        return False

    def scrape(self):
        logging.info(f"Navigating to starting URL: {BASE_URL}")
        self.driver.get(BASE_URL)
        current_page = 1  # Start from page 1

        try:
            while True:
                # Check if we've exceeded MAX_PAGES (if set)
                if MAX_PAGES and current_page > MAX_PAGES:
                    logging.info("Reached maximum page limit.")
                    break

                time.sleep(2)  # Let the page load fully
                total_downloads = len(load_records())
                logging.info(f"Currently on page {current_page}. Total downloaded so far: {total_downloads}")

                certificate_blocks = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'col-lg')]")
                logging.info(f"Found {len(certificate_blocks)} certificate blocks on page {current_page}.")

                if CERTIFICATES_PER_PAGE and CERTIFICATES_PER_PAGE > 0:
                    certificate_blocks = certificate_blocks[:CERTIFICATES_PER_PAGE]

                for block in certificate_blocks:
                    try:
                        detail_link_elem = block.find_element(By.XPATH, ".//a[contains(@href, '/view/')]")
                        detail_url = detail_link_elem.get_attribute("href")
                        file_name = block.find_element(By.XPATH, ".//h3[@class='small']").text.strip()

                        if already_downloaded(file_name):
                            logging.info(f"Skipping already downloaded certificate: {file_name}")
                            continue

                        if MAX_FILES and self.download_count >= MAX_FILES:
                            logging.info("Reached maximum download limit.")
                            return

                        self.download_certificate(detail_url, file_name)

                        # Log info after each file download
                        logging.info(f"Downloaded file '{file_name}' from page {current_page}. "
                                     f"Total downloaded so far: {len(load_records())}")

                    except Exception as e:
                        logging.error(f"Error processing certificate block: {e}")

                self.wait_for_downloads_complete(timeout=60)

                # Attempt to go to the next page
                try:
                    next_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='Next']"))
                    )
                    logging.info(f"Finished page {current_page}; navigating to page {current_page + 1}...")
                    next_button.click()
                    time.sleep(3)
                    current_page += 1
                except Exception:
                    logging.info("No 'Next' button found or an error occurred. Ending pagination.")
                    break
        except KeyboardInterrupt:
            logging.info("Scraping interrupted by user.")
        finally:
            total_downloads_final = len(load_records())
            logging.info(f"Scraping finished. Total certificates downloaded: {total_downloads_final}")

    def download_certificate(self, url, file_name):
        logging.info(f"Opening certificate URL: {url}")
        self.driver.execute_script("window.open(arguments[0]);", url)
        try:
            self.driver.switch_to.window(self.driver.window_handles[-1])
        except Exception as e:
            logging.error(f"Error switching to new tab: {e}")
            return
        try:
            pdf_link_elem = self.wait.until(
                EC.presence_of_element_located((By.ID, "blob-url"))
            )
            pdf_url = pdf_link_elem.get_attribute("href")
            logging.info(f"Found PDF URL: {pdf_url}. Navigating to download.")
            self.driver.get(pdf_url)
            self.download_count += 1
            time.sleep(2)
            self.wait_for_downloads_complete(timeout=60)

            record = {
                "output filename": file_name,
                "certificate_url": url
            }
            save_record(record)
        except KeyboardInterrupt:
            logging.info("Download interrupted by user during certificate processing.")
            raise
        except Exception as e:
            logging.error(f"Error retrieving PDF link for {url}: {e}")
        finally:
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except Exception as e:
                if "connection" in str(e).lower():
                    logging.info("Driver already disconnected, skipping tab close.")
                else:
                    logging.info(f"Error closing tab: {e}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    scraper = NYCDeathCertificateScraper(
        download_dir='./death_certificates',
        driver_path='chromedriver.exe'
    )
    try:
        scraper.scrape()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Exiting.")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
