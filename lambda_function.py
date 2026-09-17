import os
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.service import Service


def lambda_handler(event, context):

    options = webdriver.ChromeOptions()

    options.binary_location = os.environ["CHROME_BIN"]

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    options.add_argument("--window-size=1920,1080")

    # Chrome 在 Lambda container 中使用 /tmp
    options.add_argument("--user-data-dir=/tmp/chrome-profile")

    # Debug
    options.add_argument("--enable-logging")
    options.add_argument("--v=1")

    service = Service(
        executable_path=os.environ["CHROMEDRIVER"],
        log_output="/tmp/chromedriver.log"
    )

    driver = None

    try:
        print("Chrome binary:", os.environ["CHROME_BIN"])
        print("ChromeDriver:", os.environ["CHROMEDRIVER"])

        print(
            "Chrome exists:",
            os.path.exists(os.environ["CHROME_BIN"])
        )

        print(
            "ChromeDriver exists:",
            os.path.exists(os.environ["CHROMEDRIVER"])
        )

        driver = webdriver.Chrome(
            service=service,
            options=options
        )

        driver.get("https://www.google.com/maps")

        return {
            "statusCode": 200,
            "title": driver.title
        }

    except Exception as e:

        print("ERROR:")
        print(str(e))

        print("\nTRACEBACK:")
        traceback.print_exc()

        print("\nChromeDriver log:")

        try:
            with open("/tmp/chromedriver.log", "r") as f:
                print(f.read())
        except Exception as log_error:
            print("Cannot read ChromeDriver log:", log_error)

        return {
            "statusCode": 500,
            "error": str(e)
        }

    finally:

        if driver:
            driver.quit()