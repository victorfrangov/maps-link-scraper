import time
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Treat these domains as "No Website"
SOCIAL_DOMAINS = [
    "facebook.com", 
    "instagram.com", 
    "linkedin.com", 
    "yelp.ca", 
    "yellowpages.ca",
    "linktr.ee"
]
# ---------------------

def main(search_query: str, max_leads: int, headless: bool = False):
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=en-US")
    if headless:
        # modern headless flag for Chromium; fallback to "--headless" if needed
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)

    try:
        print("1. Opening Google Maps...")
        driver.get("https://www.google.com/maps")

        try:
            accept_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Accept all')]")))
            accept_btn.click()
        except:
            pass

        print(f"2. Searching for: {search_query}")
        try:
            search_box = wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
        except:
            search_box = driver.find_element(By.NAME, "q")

        search_box.clear()
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)

        print("3. Waiting for results list...")
        feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
        time.sleep(3)

        print("4. Pre-scrolling...")
        for _ in range(3):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
            time.sleep(2)

        print("5. Checking businesses...")

        leads_found = 0

        for i in range(max_leads):
            try:
                # Refresh list references
                feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
                cards = feed.find_elements(By.CSS_SELECTOR, "div[role='article']")

                if i >= len(cards):
                    print("   - No more cards loaded.")
                    break

                card = cards[i]

                # Get Name
                name = card.get_attribute("aria-label") or "Unknown Business"
                if name == "Unknown Business":
                    name = card.text.split("\n")[0]

                # Click Card
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                time.sleep(1)
                card.click()

                # Wait for Details
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                time.sleep(1.5)

                # --- NEW WEBSITE CHECK LOGIC ---
                has_valid_website = False
                found_url = ""

                # 1. Look for the Authority Button (The main Website button)
                # Google usually gives this button the attribute data-item-id="authority"
                website_btns = driver.find_elements(By.CSS_SELECTOR, "[data-item-id='authority']")

                if len(website_btns) > 0:
                    # The button exists, but let's check the URL
                    website_btn = website_btns[0]
                    found_url = website_btn.get_attribute("href")

                    if found_url:
                        # Check if the URL is in our "Block List"
                        is_social = False
                        for domain in SOCIAL_DOMAINS:
                            if domain in found_url.lower():
                                is_social = True
                                break

                        if is_social:
                            print(f"[LEAD - SOCIAL ONLY] {name} -> {found_url}")
                            # It counts as "No Valid Website", so we keep has_valid_website = False
                        else:
                            has_valid_website = True
                    else:
                        # Button exists but no URL? Assume valid to be safe.
                        has_valid_website = True

                # 2. Secondary check: If no button found, check text links just in case
                if not has_valid_website and not found_url:
                    # Look for links with "Website" text manually
                    all_links = driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        link_text = link.text or link.get_attribute("aria-label") or ""
                        if "Website" in link_text:
                            # We found a text link saying website. Check its href.
                            href = link.get_attribute("href")
                            if href:
                                is_social = False
                                for domain in SOCIAL_DOMAINS:
                                    if domain in href.lower():
                                        is_social = True
                                        break
                                if not is_social:
                                    has_valid_website = True
                            break

                # RESULT
                if not has_valid_website:
                    # If we didn't flag it as "Social Only" earlier, print as standard lead
                    if not found_url:
                        print(f"[LEAD - NO WEBSITE] {name}")

                    leads_found += 1

                # Go Back
                back_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Back']")
                back_btn.click()

                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
                time.sleep(1)

            except Exception as e:
                # If stuck, try to go back
                try:
                    driver.find_element(By.CSS_SELECTOR, "button[aria-label='Back']").click()
                    time.sleep(1)
                except:
                    pass
                continue

        print("-" * 30)
        print(f"Finished. Found {leads_found} potential leads.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Google Maps leads")
    parser.add_argument("query", help="Search query (e.g. 'Cafes in City, ST')")  # required positional
    parser.add_argument("--max", "-m", type=int, default=10, dest="max_leads", help="Max leads to process (default: 10)")
    parser.add_argument("--headless", action="store_true", help="Run Chrome headless")
    args = parser.parse_args()

    main(args.query, args.max_leads, headless=args.headless)
