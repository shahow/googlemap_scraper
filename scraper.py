from ast import Import
import os
import time
import json
import logging
import traceback
import re
import uuid

import pandas as pd
#import mymariadb as MariaDB
import snowflake_connector as sf
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DAYS = [ "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new") 
    options.add_argument("--lang=en") 
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    options.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL"}
    )
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver
def parse_popular_times_v2(htmltext,filename):
    elements = driver.find_elements(
    By.CSS_SELECTOR,
    "div[role='img']"
    )
    with open(filename, "w", encoding="utf-8") as f:
        for element in elements:
            aria = element.get_attribute("aria-label")
            if aria:
                f.write(aria + "\n")

    print(len(elements))
    return elements

def parse_popular_times(flat_data):
    """
    Parses a list of strings like "55% busy at 12 PM." into structured data.
    """
    parsed_items = []
    for item in flat_data:
        # Regex to find percentages and time
        match = re.search(r"(\d+)% busy at (\d+)(?:\u202f)?(AM|PM)", item)
        if not match:
            # "0% busy" might be different? "Usually 0%..."
            match = re.search(r"Usually (\d+)% busy at (\d+)(?:\u202f)?(AM|PM)", item)
        
        if match:
             pct = int(match.group(1))
             hour = int(match.group(2))
             ampm = match.group(3)
             if ampm == "PM" and hour != 12:
                 hour += 12
             elif ampm == "AM" and hour == 12:
                 hour = 0
             parsed_items.append({"hour": hour, "occupancy": pct, "raw": item})
        else:
            # "Currently 50% busy"
            match_curr = re.search(r"Currently (\d+)% busy", item)
            if match_curr:
                parsed_items.append({"hour": "Now", "occupancy": int(match_curr.group(1)), "raw": item})
            else:
                 # "0% busy"
                 if "0% busy" in item:
                     parsed_items.append({"hour": "?", "occupancy": 0, "raw": item})

    # Group by days
    days = []
    day_chunk = []
    last_hour = -1
    
    for item in parsed_items:
        h = item["hour"]
        if isinstance(h, int):
            if h < last_hour and last_hour != -1:
                days.append(day_chunk)
                day_chunk = []
            last_hour = h
        day_chunk.append(item)
    
    if day_chunk:
        days.append(day_chunk)
        
    return days

def get_place_urls(driver, query):
    """
    Searches for a query and extracts all place URLs from the results list.
    """
    logging.info(f"Searching for: {query}")
    driver.get("https://www.google.com/maps")
    wait = WebDriverWait(driver, 10)
    
    search_input = None
    selectors = [
        (By.ID, "searchboxinput"),
        (By.NAME, "q"),
        (By.CSS_SELECTOR, "input[aria-label='Search Google Maps']"),
    ]
    
    for by, val in selectors:
        try:
            search_input = wait.until(EC.element_to_be_clickable((by, val)))
            break
        except:
            continue
            
    if not search_input:
        logging.error("Could not find search input.")
        return []

    search_input.clear()
    search_input.send_keys(query)
    search_input.send_keys(Keys.ENTER)
    
    time.sleep(3)
    
    try:
        results_feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
        
        logging.info("Found results list. Scrolling to load more...")
        
        for _ in range(5): 
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_feed)
            time.sleep(1.5)
            
        anchors = results_feed.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")
        urls = set()
        for a in anchors:
            href = a.get_attribute("href")
            if href:
                urls.add(href.split("?")[0])
        
        logging.info(f"Found {len(urls)} places.")
        return list(urls)

    except TimeoutException:
        logging.info("No results list found. Checking if single result loaded directly.")
        try:
            current_url = driver.current_url
            if "/maps/place/" in current_url:
                logging.info("Single result found.")
                return [current_url]
        except:
            pass
            
    return []

def get_realtime_busy(driver):
    elements = driver.find_elements(
        By.XPATH,
        "//*[normalize-space(text())='即時' or normalize-space(text())='Live']"
    )

    if not elements:
        return None

    try:
        busy_element = elements[0].find_element(
            By.XPATH,
            "./following-sibling::*[1]"
        )

        return busy_element.text.strip()

    except Exception:
        return None

def scrape_place(driver, url, original_query):
    logging.info(f"Scraping place URL: {url}")
    driver.get(url)
    time.sleep(3) # Wait for load

    logs = driver.get_log("performance")
    for entry in logs:
        try:
            message = json.loads(entry["message"])["message"]

            if message["method"] != "Network.responseReceived":
                continue
            
            #logging.info(f"Processing performance log: {message}")
            response = message["params"]["response"]
            request_id = message["params"]["requestId"]
            response_url = response["url"]

            if "/maps/preview/place" not in response_url:
                continue

            logging.info(
                f"Found /maps/preview/place: "
                f"{response.status} {response_url}"
            )

            try:
                result = driver.execute_cdp_cmd(
                    "Network.getResponseBody",
                    {"requestId": request_id}
                )

                body = result.get("body", "")

                filename = os.path.join(
                    "sponse_dir",
                    f"{safe_name}.txt"
                )

                #with open(filename, "w", encoding="utf-8") as f:
                #    f.write(body)

                logging.info(
                    f"Saved place response: {filename} "
                    f"({len(body)} chars)"
                )

                response_index += 1

            except Exception as e:
                logging.warning(
                    f"Could not get response body for "
                    f"{response_url}: {e}"
                )

        except Exception as e:
            logging.warning(f"Error processing performance log: {e}")
    
    wait = WebDriverWait(driver, 10)
    place_name = "Unknown"
    try:
        h1 = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        place_name = h1.text
        logging.info(f"Place Name: {place_name}")
    except:
        pass

    driver.execute_script("window.scrollBy(0, 500);")
    time.sleep(3)

    elements = driver.find_elements(
        By.XPATH,
        "//*[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'busy')]"
    )

    for i, el in enumerate(elements[:100]):
        try:
            logging.info(
            f"BUSY[{i}] tag={el.tag_name}, "
            f"aria-label={el.get_attribute('aria-label')}, "
            f"text={el.text}"
            )
        except Exception:
            pass

    visible_data = []

    for b in elements:
        aria = b.get_attribute("aria-label")
        if aria:
            visible_data.append(aria)

    logging.info("========== RAW BUSY DATA ==========")

    #for i, item in enumerate(visible_data):
    #    logging.info(f"[{i}] {item}")

    #html = driver.page_source
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", place_name)

    #with open(f"debug_{safe_name}.html", "w", encoding="utf-8") as f:
    #    f.write(driver.page_source)

    logging.info("========== END RAW BUSY DATA ==========")
    elements = driver.find_elements(
    By.CSS_SELECTOR,
    "div[role='img']"
)
    buttons = driver.find_elements(By.CSS_SELECTOR, "button.CsEnBe")
    #print("address: " + buttons[0].get_attribute("aria-label"))
    

    nurl = driver.current_url
    nowurl = nurl.replace("https://www.google.com/maps/place/", "")
    #print("nowurl: " +  nowurl)
    coordinates = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", nowurl)
    if coordinates:
        latitude, longitude = coordinates.groups()
    else:
        coordinates = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", nowurl)
        if not coordinates:
            raise ValueError(f"Could not find coordinates in Maps URL: {nurl}")
        latitude, longitude = coordinates.groups()
   
    print("place name: " + place_name)
    print("latitude: " + latitude)
    print("longitude: " + longitude)

    star = ""
    busydata = {day: [] for day in DAYS}
    day_index = 0
    previous_hour = None
    for a in elements:
        text = a.get_attribute("aria-label") or ""
        #print("this is the aria-label: " + text)
        if text.endswith(("顆星", "stars")):
            rating = re.search(r"(\d+(?:\.\d+)?)", text)
            star = rating.group(1) if rating else ""
            #print("star: " + star)
        m = re.search(r'(\d+)時的繁忙程度通常為\s*(\d+)%', text)

        if m:
            hour, busy = m.groups()
            hour = int(hour)
            if previous_hour is not None and hour < previous_hour:
                day_index += 1
            if day_index < len(DAYS):
                busydata[DAYS[day_index]].append({
                    "hour": hour,
                    "occupancy": int(busy),
                    "raw": text,
                })
            previous_hour = hour
    #cursor.close()
    #conn.close()
    busystatus = get_realtime_busy(driver)
    
    return {
        "query": original_query,
        "name": place_name,
        "url": url,
        "latitude": latitude,
        "longitude": longitude,
        "star": star,
        "address": buttons[0].get_attribute("aria-label") if buttons else "",
        "popular_times": busydata,
        "busystatus": busystatus
    }

def main(queries=None):
    if queries is None:
        logging.error("queries not found.")
        return []

    all_results = []
    driver = None
    
    try:
        driver = get_driver()
        
        for query in queries:  # Limit to first query for debugging
            urls = get_place_urls(driver, query)
            
            for url in urls[:1]:  # Limit to first 1 URL for debugging
                try:
                    data = scrape_place(driver, url, query)
                    if data:
                        all_results.append(data)
                except Exception as e:
                    logging.error(f"Error scraping {url}: {e}")
                    continue
                    
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

    # Save JSON
    with open("popular_times.json", "w") as f:
        json.dump(all_results, f, indent=4)
    logging.info(f"Scraping completed. Found data for {len(all_results)} places. Saved to popular_times.json")

    # Read the JSON and write place and popular-times data to MariaDB.
    conn = sf.getConn()
    cursor = conn.cursor()
    try:
        call_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO GMAP_DB.PUBLIC.CALL_LOG (call_id)
            VALUES (%s)
        """, (call_id,))

        location_sql = """
            INSERT INTO location (name, address, latitude, longitude,star)
            SELECT ?, ?, ?, ?, ? FROM DUAL
            WHERE NOT EXISTS (
                SELECT 1 FROM location
                WHERE name = ? AND address = ? AND latitude = ? AND longitude = ? AND star = ?
            )
        """
        popular_times_sql = """
            INSERT INTO location_busy
                (location_id,call_id, hour,busy,weekday)
          VALUES (?, ?, ?, ?, ?)
        """

        busystatus_sql = """
            INSERT INTO busystatus
                (location_id, call_id, busystatus)   
                VALUES (?, ?, ?)"""

        imported_rows = 0
        for entry in all_results:
            name = str(entry.get("name") or "Unknown")
            address = (entry.get("address") or "").replace("地址: ", "", 1)
            latitude = entry.get("latitude") or None
            longitude = entry.get("longitude") or None
            star = entry.get("star") or None
            busystatus = entry.get("busystatus") or None

            cursor.execute(location_sql, (
                name, address, latitude, longitude, star,
                name, address, latitude, longitude, star
            ))

            cursor.execute("SELECT id FROM location WHERE name = ? AND address = ? AND latitude = ? AND longitude = ?", (name, address, latitude, longitude))
            location_id = cursor.fetchone()[0]


            popular_times = entry.get("popular_times") or {}
            print(f"Processing popular_times for {name}: {popular_times}")
            for day_name in DAYS:
                for hour_data in popular_times.get(day_name, []):
                    hour = hour_data.get("hour")
                    occupancy = hour_data.get("occupancy")
                    print(f"Day: {day_name}, Hour: {hour}, Occupancy: {occupancy}")
                    if not isinstance(hour, int) or not 0 <= hour <= 23:
                        continue
                    if not isinstance(occupancy, int) or not 0 <= occupancy <= 100:
                        continue
                    
                    cursor.execute(popular_times_sql, (
                        location_id, call_id, hour, occupancy, day_name
                    ))
                    
                    imported_rows += 1

            if busystatus is not None:
                cursor.execute(busystatus_sql, (location_id, call_id, busystatus))

        conn.commit()
        logging.info("Imported %d popular-times rows into MariaDB", imported_rows)
    except Exception:
        conn.rollback()
        logging.exception("Could not write popular-times data to MariaDB")
        raise
    finally:
        cursor.close()
        conn.close()


#if __name__ == "__main__":
#    main()

def lambda_handler(event, context):
    queries = event.get("queries", [])

    if isinstance(queries, str):
        queries = [queries]

    if not queries:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "queries is required"})
        }

    results = main(queries)

    return {
        "statusCode": 200,
        "body": json.dumps(results, ensure_ascii=False)
    }

if __name__ == "__main__":
    event = {
        "queries": [
            "Starbucks Taipei",
            "Coffee shop Taichung"
        ]
    }

    lambda_handler(event, None)