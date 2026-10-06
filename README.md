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

  ## Future Architecture

### S3 → SQS → Lambda → Snowflake

The crawler can be further improved by separating data collection from database ingestion.

Instead of writing directly to Snowflake, the Selenium crawler stores each location's result as a JSON file in Amazon S3.

```text
Google Maps
     │
     ▼
EC2 Selenium Crawler
     │
     │ JSON
     ▼
Amazon S3
     │
     │ ObjectCreated Event
     ▼
Amazon SQS
     │
     │ Batch Messages
     ▼
AWS Lambda
     │
     │ Batch Processing
     ▼
Snowflake
```

### Architecture Components

**EC2 Selenium Crawler**

Runs the Google Maps scraper and collects location information, popular times, and busy data. Each scraped location is saved as an individual JSON file.

**Amazon S3**

Acts as the raw data storage layer. Keeping the original JSON data in S3 allows the data to be reprocessed later without scraping Google Maps again.

**Amazon SQS**

Receives S3 object creation events and provides a queue between the crawler and the database loader. This allows the crawler to produce data continuously without waiting for Snowflake ingestion.

**AWS Lambda**

Consumes SQS messages in batches, retrieves the corresponding JSON files from S3, transforms the data, and loads the results into Snowflake.

**Snowflake**

Stores the processed location, busy-time, and crawler execution data. Batch loading can be used to reduce the overhead of individual database inserts.

### Overall Data Flow

```text
                    ┌─────────────────┐
                    │   Google Maps   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ EC2 Selenium    │
                    │    Crawler      │
                    └────────┬────────┘
                             │
                          JSON
                             │
                             ▼
                    ┌─────────────────┐
                    │       S3        │
                    │   Raw Storage   │
                    └────────┬────────┘
                             │
                      ObjectCreated
                             │
                             ▼
                    ┌─────────────────┐
                    │      SQS        │
                    │ Queue / Buffer  │
                    └────────┬────────┘
                             │
                           Batch
                             │
                             ▼
                    ┌─────────────────┐
                    │     Lambda      │
                    │ Data Ingestion  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Snowflake    │
                    │   GMAP_DB       │
                    └─────────────────┘
```

This architecture decouples the crawler from the database layer, provides buffering and retry capabilities through SQS, and allows Snowflake ingestion to be processed independently from Google Maps scraping.

