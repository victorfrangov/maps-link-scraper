import time
import argparse
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
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
        time.sleep(1)

        print("4. Pre-scrolling...")
        for _ in range(3):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
            time.sleep(0.5)

        print("5. Checking businesses...")

        leads_found = 0
        leads = []  # collect rows for Excel

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
                time.sleep(0.2)
                card.click()

                # Wait for Details
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                time.sleep(0.5)

                # --- WEBSITE CHECK LOGIC ---
                has_valid_website = False
                found_url = ""
                website_type = "none"

                website_btns = driver.find_elements(By.CSS_SELECTOR, "[data-item-id='authority']")

                if len(website_btns) > 0:
                    website_btn = website_btns[0]
                    found_url = website_btn.get_attribute("href") or ""
                    if found_url:
                        is_social = any(domain in found_url.lower() for domain in SOCIAL_DOMAINS)
                        if is_social:
                            website_type = "social"
                            print(f"[LEAD - SOCIAL ONLY] {name} -> {found_url}")
                        else:
                            website_type = "valid"
                            has_valid_website = True
                    else:
                        website_type = "valid"
                        has_valid_website = True

                # Secondary check for textual "Website" links
                if not has_valid_website and not found_url:
                    all_links = driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        link_text = (link.text or link.get_attribute("aria-label") or "").strip()
                        if "Website" in link_text:
                            href = link.get_attribute("href") or ""
                            found_url = href
                            if href:
                                is_social = any(domain in href.lower() for domain in SOCIAL_DOMAINS)
                                website_type = "social" if is_social else "valid"
                                if not is_social:
                                    has_valid_website = True
                            break

                # --- PHONE PARSING ---
                phone = "Not found"
                try:
                    # 1) Look for tel: links (most reliable)
                    tel_links = driver.find_elements(By.XPATH, "//a[starts-with(@href,'tel:')]")
                    if tel_links:
                        raw = tel_links[0].get_attribute("href").replace("tel:", "").strip()
                        phone = re.sub(r'[^\d\+]', '', raw)
                    else:
                        # 2) Fallback: search text in the details panel near the business name
                        try:
                            h1 = driver.find_element(By.TAG_NAME, "h1")
                            panel = h1.find_element(By.XPATH, "ancestor::div[1]")
                            panel_text = panel.text
                        except Exception:
                            panel_text = driver.find_element(By.TAG_NAME, "body").text
                        phone_match = re.search(r'(\+?\d[\d\-\s\(\)\.]{6,}\d)', panel_text)
                        if phone_match:
                            raw = phone_match.group(1).strip()
                            phone = re.sub(r'[^\d\+]', '', raw)
                except Exception:
                    phone = "Not found"

                # --- ADDRESS (best-effort) ---
                address = "Not found"
                try:
                    addr_elems = driver.find_elements(By.CSS_SELECTOR, "[data-item-id='address'], [aria-label*='Address']")
                    if addr_elems:
                        address = addr_elems[0].text or addr_elems[0].get_attribute("aria-label") or "Not found"
                    else:
                        # fallback: try to capture lines near the name header
                        panel_text = driver.find_element(By.TAG_NAME, "body").text
                        # heuristic: look for a line containing a digit + street
                        addr_match = re.search(r'\d{1,5}\s+[A-Za-z0-9\.\-]+\s+[A-Za-z]+', panel_text)
                        if addr_match:
                            address = addr_match.group(0).strip()
                except Exception:
                    address = "Not found"

                # RESULT handling
                if website_type != "valid":
                    if website_type == "none":
                        print(f"[LEAD - NO WEBSITE] {name}")
                    elif website_type == "social":
                        print(f"[LEAD - SOCIAL ONLY] {name} -> {found_url}")
                    leads_found += 1
                    # collect lead row (only for leads without a valid website)
                    leads.append({
                        "name": name,
                        "website": found_url or "",
                        "website_type": website_type,
                        "phone": phone,
                        "address": address
                    })

                # Go Back
                try:
                    back_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Back']")
                    back_btn.click()
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
                    time.sleep(0.5)
                except:
                    pass

            except Exception:
                try:
                    driver.find_element(By.CSS_SELECTOR, "button[aria-label='Back']").click()
                    time.sleep(0.5)
                except:
                    pass
                continue

        print("-" * 30)
        print(f"Finished. Found {leads_found} potential leads.")

        # --- WRITE TO EXCEL ---
        try:
            out_dir = Path.cwd()
            # filename based on sanitized query -> append when same query
            safe_query = re.sub(r'[^A-Za-z0-9]+', '_', search_query).strip('_').lower()[:64] or "results"
            out_file = out_dir / f"leads_{safe_query}.xlsx"

            new_df = pd.DataFrame(leads, columns=["name", "website", "website_type", "phone", "address"])

            if out_file.exists():
                try:
                    existing = pd.read_excel(out_file)
                    combined = pd.concat([existing, new_df], ignore_index=True)
                    combined.drop_duplicates(subset=["name", "address", "phone", "website"], inplace=True)
                except Exception:
                    combined = new_df
            else:
                combined = new_df

            combined.to_excel(out_file, index=False)
            print(f"Saved leads to: {out_file}")
        except Exception as e:
            print(f"Failed to write Excel: {e}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        time.sleep(0.5)
        driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Google Maps leads")
    parser.add_argument("query", help="Search query (e.g. 'Cafes in City, ST')")  # required positional
    parser.add_argument("--max", "-m", type=int, default=10, dest="max_leads", help="Max leads to process (default: 10)")
    parser.add_argument("--headless", action="store_true", help="Run Chrome headless")
    args = parser.parse_args()

    main(args.query, args.max_leads, headless=args.headless)
