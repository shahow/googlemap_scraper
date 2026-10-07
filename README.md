# Google Maps Busy Times Scraper

A Python/Selenium-based scraper for collecting **Google Maps Popular Times / Busy Times** data and storing the results in **Snowflake**.

The project is designed to run both locally and in an AWS container environment. It uses Chrome + Selenium to load Google Maps pages and captures the underlying network response containing the Popular Times / Busy data.

---

## Features

* Search Google Maps places by query
* Use Selenium + Chrome to load Google Maps
* Capture Google Maps network responses through Chrome DevTools Protocol (CDP)
* Extract Popular Times / Busy Times data
* Support Traditional Chinese Google Maps content
* Run locally with Docker
* Run as an AWS Lambda container image
* Store scraped data in Snowflake
* Support batch processing of multiple locations
* Record scraping execution information through `call_id`
* Designed to reduce unnecessary browser memory usage and request processing

---

## Architecture

```text
                         ┌────────────────────┐
                         │  Queries Location  │
                         │  from datbase      │
                         │ ["Location A", ...]│
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │  uv run scraper.py │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Selenium + Chrome  │
                         │                    │
                         │ Google Maps        │
                         └─────────┬──────────┘
                                   │
                         CDP Network Response
                                   │
                                   ▼
                         ┌────────────────────┐
                         │  Busy Data Parser  │
                         │                    │
                         │ Popular Times      │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │     Snowflake      │
                         │     store data     │
                         └────────────────────┘
```

---

## Project Structure

```text
scraper.py
busyparset.py
Dockerfile
pyproject.toml
uv.lock
requirements.txt
README.md
```

---

## Technologies

* Python 3.12
* Selenium
* Google Chrome
* ChromeDriver
* Docker
* AWS Lambda
* Amazon ECR
* Snowflake
* Snowflake Python Connector
* Chrome DevTools Protocol (CDP)
* `uv`
