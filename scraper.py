from ast import Import
from datetime import datetime
import os
import platform
import time
import json
import logging
import traceback
import re
import uuid

from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from requests import request
import requests
#import mymariadb as MariaDB
from busyparser import parse_busydata
import snowflake_connector as sf
from get_weather import save_weather_data_to_snowflake,save_txt
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

DAYS = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

try:
    import psutil
except ImportError:
    psutil = None
call_id = str(uuid.uuid4())

def get_driver():
    options = webdriver.ChromeOptions()

    system = platform.system()
    is_lambda = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

    # =====================================================
    # AWS Lambda
    # =====================================================
    if is_lambda:
        print("Environment: AWS Lambda")

        options.binary_location = os.environ["CHROME_BIN"]

        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        options.add_argument("--lang=zh-TW")
        options.add_argument("--accept-lang=zh-TW,zh")
        options.add_argument("--window-size=1920,1080")

        options.add_argument("--user-data-dir=/tmp/chrome-profile")

        options.add_argument("--enable-logging")
        options.add_argument("--v=1")

        options.set_capability(
            "goog:loggingPrefs",
            {"performance": "ALL"}
        )

        options.page_load_strategy = "eager"

        service = ChromeService(
            executable_path=os.environ["CHROMEDRIVER"],
            log_output="/tmp/chromedriver.log"
        )

    # =====================================================
    # Linux EC2 / Docker
    # =====================================================
    elif system == "Linux":
        print("Environment: Linux / EC2 / Docker")

        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        options.add_argument("--lang=zh-TW")
        options.add_argument("--accept-lang=zh-TW,zh")
        options.add_argument("--window-size=1920,1080")

        # 先跟 Windows 成功環境保持一致
        options.add_argument(
            "user-agent=Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        )

        options.set_capability(
            "goog:loggingPrefs",
            {"performance": "ALL"}
        )

        options.page_load_strategy = "eager"

        service = ChromeService()

    # =====================================================
    # Windows
    # =====================================================
    else:
        print("Environment: Windows / Local")
        options.add_argument("--headless=new")

        options.add_argument("--lang=zh-TW")
        options.add_argument("--accept-lang=zh-TW,zh")
        options.add_argument("--start-maximized")

        options.add_argument(
            "user-agent=Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        )

        options.set_capability(
            "goog:loggingPrefs",
            {"performance": "ALL"}
        )

        options.page_load_strategy = "eager"

        service = ChromeService()

    return webdriver.Chrome(
        service=service,
        options=options
    )

def getbusystr(body):
    targetlist = [ '[1,[[','[2,[[','[3,[[','[4,[[','[5,[[','[6,[[']
    firstquote = body.index('[[[7,')
    print("firstquote:", firstquote)
    #secondquote = body.index('[1,[[', firstquote)
    #print("secondquote:", secondquote) 
    #print(body[firstquote:secondquote]) 
    firststart = -1
    for a in targetlist:
        if a in body:
            start = body.index(a)
            if firststart == -1:
                firststart = start
            end = body.find(']],', start) + 3
            if end != -1:
                print("start:", start, "end:", end)
                busystr = body[start:end]
                print("busystr:", busystr)
                #save_txt(busystr)
    end = body.find(']],', end) + 3
    busystr = body[firststart:end]
    print("busystr:", busystr)
    return busystr



def log_memory(label):
    if psutil:
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / 1024 / 1024
        logging.info(f"[MEM] {label}: Python RSS={mem:.1f} MB")

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


def fetch_response_body_safely(driver, request_id, response_url):
    try:
        return driver.execute_cdp_cmd(
            "Network.getResponseBody",
            {"requestId": request_id}
        )["body"]
    except Exception as e:
        error_text = str(e).lower()
        ignore_patterns = (
            "no resource with given identifier found",
            "failed to load response body",
            "response body is unavailable",
            "response not found",
            "request is not available",
        )
        if any(pattern in error_text for pattern in ignore_patterns):
            logging.debug(
                "Skipping unavailable response body for %s: %s",
                response_url,
                e,
            )
            return None
        raise


def scrape_place(driver, url, original_query):
    logging.info(f"Scraping place URL: {url}")
    log_memory("before driver.get")
    driver.get(url)
    log_memory("after driver.get")
    
    #time.sleep(5) # Wait for load

    wait = WebDriverWait(driver, 30)
    place_name = "Unknown"
    try:
        h1 = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        place_name = h1.text.strip()
        logging.info(f"Place Name: {place_name}")
    except Exception:
        pass

    safe_name = re.sub(r'[\\/*?:"<>|]', "_", place_name)
    time.sleep(8)

    logs = driver.get_log("performance")

    response_index = 0
    busydata = []
    google_place_id = None
    for entry in logs:
        try:
            message = json.loads(
                entry["message"]
            )["message"]

            if message["method"] != "Network.responseReceived":
                continue

            response = message["params"]["response"]
            request_id = message["params"]["requestId"]
            response_url = response["url"]
            
            # 只處理 /maps/preview/place
            if "/maps/preview/place" not in response_url:
                continue

         
            logging.info(
                f"Found /maps/preview/place: "
                f"{response.get('status', 'unknown')} {response_url}"
            )

            try:
                log_memory("before getResponseBody")
                print("request_id in try: " + request_id)
                body = fetch_response_body_safely(driver, request_id, response_url)
                if body is None:
                    continue

                logging.info(f"body size={len(body):,}")
                logging.info(f"body preview={body[:2000]}")
                busystr = getbusystr(body)
                cnt=busystr.count(']],')
                if cnt == 7:
                    busydata = parse_busydata(body)

                place_id_match = re.search(
                    r'placeid(?:=|\\u003d)(ChIJ[A-Za-z0-9_-]+)',
                    body
                )

                if place_id_match:
                    google_place_id = place_id_match.group(1)
                else:
                    google_place_id = None

                print(f"google_place_id: {google_place_id}")
                print(f"busydata: {busydata}")

                for row in busydata:
                    logging.info(row)

                log_memory("after getResponseBody")

                temp_filename = (
                    f"{safe_name}_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
                    f"{response_index}.txt"
                )
                is_aws = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
                if is_aws:
                    temp_filename = (
                        f"/tmp/{safe_name}_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
                        f"{response_index}.txt"
                    )

                print(temp_filename)
                with open(
                    temp_filename,
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write(body)

                logging.info(
                    f"Saved place response: "
                    f"{temp_filename} "
                    f"({len(body)} chars)"
                )

                response_index += 1

            except Exception as e:
                logging.exception(
                    f"Could not process response body for "
                    f"{response_url}"
                )

        except Exception as e:

            logging.warning(
                f"Error processing performance log: {e}"
            )

    del logs
    driver.execute_script(
        "window.scrollBy(0, 500);"
    )
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

    with open(f"debug_{safe_name}.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    logging.info("========== END RAW BUSY DATA ==========")
    logging.info("========== START GET PLACE INFO========")
    elements = driver.find_elements(
    By.CSS_SELECTOR,
    "div[role='img']")
    
    buttons = driver.find_elements(By.CSS_SELECTOR, "button.CsEnBe")
  
    nurl = driver.current_url
    nowurl = nurl.replace("https://www.google.com/maps/place/", "")
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
    print("busydata: " + str(busydata))
    print("google_place_id: " + str(google_place_id))
  
    for a in elements:
        text = a.get_attribute("aria-label") or ""
        #print("this is the aria-label: " + text)
        if text.endswith(("顆星", "stars")):
            rating = re.search(r"(\d+(?:\.\d+)?)", text)
            star = rating.group(1) if rating else ""
            #print("star: " + star)
        #logging.info("Start get single busy data")
        """
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
        """
        #logging.info("End get single busy data")
    
    busystatus = get_realtime_busy(driver)
    print("busystatus: " + str(busystatus))
    print("address: " + buttons[0].get_attribute("aria-label") if buttons else "")

    insert_into_snowflake({
        "query": original_query,
        "name": place_name,
        "url": url,
        "latitude": latitude,
        "longitude": longitude,
        "star": star,
        "address": buttons[0].get_attribute("aria-label") if buttons else "",
        "popular_times": busydata,
        "busystatus": busystatus,
        "google_place_id": google_place_id
    })

def insert_into_snowflake(entry):
    location_sql = """
                INSERT INTO GMAP_DB.PUBLIC.location (call_id,name, address, latitude, longitude, google_place_id)
                SELECT %s, %s, %s, %s, %s,%s 
                WHERE NOT EXISTS (
                    SELECT 1 FROM GMAP_DB.PUBLIC.location
                    WHERE google_place_id = %s
    
                )
            """
       # Optional: small delay to ensure the commit is processed
    popular_times_sql = """
                INSERT INTO GMAP_DB.PUBLIC.location_busy
                    (location_id,call_id, hour,busy,weekday)
                    VALUES (%s, %s, %s, %s, %s)
            """
    
    star_sql = """
            INSERT INTO GMAP_DB.PUBLIC.location_star
                (GOOGLE_PLACE_ID, call_id, star)        
                VALUES (%s, %s, %s)
                """
    
    busystatus_sql = """
                INSERT INTO GMAP_DB.PUBLIC.busystatus
                    (location_id, call_id, busystatus)   
                    VALUES (%s, %s, %s)"""
    name = str(entry.get("name") or "Unknown")
    address = (entry.get("address") or "").replace("地址: ", "", 1)
    latitude = entry.get("latitude") or None
    longitude = entry.get("longitude") or None
    star = entry.get("star") or None
    busystatus = entry.get("busystatus") or None
    google_place_id = entry.get("google_place_id") or None
    
    location_id = None
    conn = sf.getConn()
    cursor = conn.cursor()
    cursor.execute("ALTER SESSION SET TIMEZONE = 'Asia/Taipei'")

    if google_place_id:         
        cursor.execute(location_sql, (
                    call_id, name, address, latitude, longitude, google_place_id, google_place_id
                    ))
               
        cursor.execute("SELECT id FROM GMAP_DB.PUBLIC.location WHERE google_place_id = %s", (google_place_id,))
        location_id = cursor.fetchone()[0]
    
        popular_times = entry.get("popular_times") or {}
        print(f"Processing popular_times for {name}: {popular_times}")
        popularlist=[]
    
        print(f"location_id: {location_id}")
        for dayindex in range(1, 8):
            filtered_days = [d for d in popular_times if d.get("weekday") == dayindex]
            print(f"Filtered days for {dayindex}: {filtered_days}")
    
            for hour_data in filtered_days:
                hour = hour_data.get("hour")
                occupancy = hour_data.get("busy")
                #print(f"Day: {day_name}, Hour: {hour}, Occupancy: {occupancy}")
                if not isinstance(hour, int) or not 0 <= hour <= 23:
                    continue
                if not isinstance(occupancy, int) or not 0 <= occupancy <= 100:
                    continue
                popularlist.append((location_id, call_id, hour, occupancy, DAYS[dayindex]))

            imported_rows = 0
            if len(popularlist) > 0 and location_id is not None:
                cursor.executemany(popular_times_sql, popularlist)
                imported_rows += len(popularlist)
    
        if busystatus is not None and location_id is not None:
            cursor.execute(busystatus_sql, (location_id, call_id, busystatus))
        if star is not None and location_id is not None:
            cursor.execute(star_sql, (google_place_id, call_id, star))
    conn.commit()
    cursor.close()
    conn.close()

def main(query=None):
    if query is None:
        logging.error("Query not found.")
        return []

    all_results = []
    driver = None
    
    try:
        driver = get_driver()
        
        #for query in queries:  # Limit to first query for debugging
        urls = get_place_urls(driver, query)
            
        for url in urls:  # Limit to first 1 URL for debugging
            try:
                data = scrape_place(driver, url, query)
                if data:
                    all_results.append(data)
            except Exception as e:
                logging.error(f"Error scraping {url}: {e}")
                traceback.print_exc()

                    # ChromeDriver 可能已經卡死，直接重建
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None
                try:
                    driver = get_driver()
                    logging.info("ChromeDriver restarted after scraping error.")
                except Exception as restart_error:
                    logging.error(
                        f"Failed to restart ChromeDriver: {restart_error}"
                    )
                    

                continue
                #finally:
                #    driver.quit()
                    
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
    cursor.execute("ALTER SESSION SET TIMEZONE = 'Asia/Taipei'")
    try:  
        
        location_sql = """
            INSERT INTO GMAP_DB.PUBLIC.location (call_id,name, address, latitude, longitude, google_place_id)
            SELECT %s, %s, %s, %s, %s,%s 
            WHERE NOT EXISTS (
                SELECT 1 FROM GMAP_DB.PUBLIC.location
                WHERE google_place_id = %s

            )
        """
   # Optional: small delay to ensure the commit is processed
        popular_times_sql = """
            INSERT INTO GMAP_DB.PUBLIC.location_busy
                (location_id,call_id, hour,busy,weekday)
                VALUES (%s, %s, %s, %s, %s)
        """

        star_sql = """
        INSERT INTO GMAP_DB.PUBLIC.location_star
            (GOOGLE_PLACE_ID, call_id, star)        
            VALUES (%s, %s, %s)
            """

        busystatus_sql = """
            INSERT INTO GMAP_DB.PUBLIC.busystatus
                (location_id, call_id, busystatus)   
                VALUES (%s, %s, %s)"""

        imported_rows = 0
        for entry in all_results:
            name = str(entry.get("name") or "Unknown")
            address = (entry.get("address") or "").replace("地址: ", "", 1)
            latitude = entry.get("latitude") or None
            longitude = entry.get("longitude") or None
            star = entry.get("star") or None
            busystatus = entry.get("busystatus") or None
            google_place_id = entry.get("google_place_id") or None

            location_id = None
            if google_place_id:
                
                cursor.execute(location_sql, (
                call_id, name, address, latitude, longitude, google_place_id, google_place_id
                ))
           
                cursor.execute("SELECT id FROM GMAP_DB.PUBLIC.location WHERE google_place_id = %s", (google_place_id,))
                location_id = cursor.fetchone()[0]


            popular_times = entry.get("popular_times") or {}
            print(f"Processing popular_times for {name}: {popular_times}")
            popularlist=[]

            print(f"location_id: {location_id}")
            for dayindex in range(1, 8):
                filtered_days = [d for d in popular_times if d.get("weekday") == dayindex]
                print(f"Filtered days for {dayindex}: {filtered_days}")

                for hour_data in filtered_days:
                    hour = hour_data.get("hour")
                    occupancy = hour_data.get("busy")
                    #print(f"Day: {day_name}, Hour: {hour}, Occupancy: {occupancy}")
                    if not isinstance(hour, int) or not 0 <= hour <= 23:
                        continue
                    if not isinstance(occupancy, int) or not 0 <= occupancy <= 100:
                        continue
                    popularlist.append((location_id, call_id, hour, occupancy, DAYS[dayindex]))

            if len(popularlist) > 0 and location_id is not None:
                cursor.executemany(popular_times_sql, popularlist)
                imported_rows += len(popularlist)

            if busystatus is not None and location_id is not None:
                cursor.execute(busystatus_sql, (location_id, call_id, busystatus))
            if star is not None and location_id is not None:
                cursor.execute(star_sql, (google_place_id, call_id, star))
        conn.commit()
        try:
            save_weather_data_to_snowflake(conn, call_id)
        except Exception:
            logging.exception("Weather data collection failed")
        #save_weather_data_to_snowflake(conn, call_id)

        
        logging.info("Imported %d popular-times rows into GMAP_DB.PUBLIC.location_busy", imported_rows)
    except Exception:
        conn.rollback()
        logging.exception("Could not write popular-times data to GMAP_DB.PUBLIC.location_busy")
        raise
    finally:
        cursor.close()
        conn.close()

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
    #check location_busy table
    busystatus_sql = "SELECT * FROM GMAP_DB.PUBLIC.BUSYSTATUS WHERE CALL_ID = '32175138-dfb7-4ad5-9aef-dff2b3c401fb';"

    


    return {
        "statusCode": 200,
        "body": json.dumps(results, ensure_ascii=False)
    }

def run_parallel(locations, batch_size=5):

    all_results = []

    for i in range(0, len(locations), batch_size):

        batch = locations[i:i + batch_size]

        logging.info(
            f"Processing locations {i + 1} ~ {i + len(batch)}"
        )

        with ThreadPoolExecutor(max_workers=2) as executor:

            futures = {
                executor.submit(main, location): location
                for location in batch
            }

            for future in as_completed(futures):

                location = futures[future]

                try:
                    results = future.result()

                    if results:
                        all_results.extend(results)

                except Exception as e:
                    logging.error(
                        f"Worker failed for {location}: {e}"
                    )

    return all_results

if __name__ == "__main__":
    """
    event = {
        "queries": [
            "東喜堂花園茶館",
            #"Starbucks Taipei",
         #   "Coffee shop Taichung"
        ]
    }
    """
    event = {}
    conn = sf.getConn()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT NAME FROM GMAP_DB.PUBLIC.LOCATION;")
    locations = [record[0] for record in cursor.fetchall()]
    event["queries"] = locations
    cursor.execute("ALTER SESSION SET TIMEZONE = 'Asia/Taipei'")
    cursor.execute("""
                INSERT INTO GMAP_DB.PUBLIC.CALL_LOG (call_id)
                VALUES (%s)
            """, (call_id,))
    
    cursor.close()
    conn.close()

    seen = set()
    duplicates = []
    
    print(event)
    #lambda_handler(event, None)
    results = run_parallel(locations,batch_size=2)

