import requests
from datetime import datetime
import boto3
from dotenv import load_dotenv
import os
import snowflake_connector as sf
import uuid

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

def flatten_dict(data, parent_key=''):
    """
    將巢狀 JSON 展平成一層 dictionary
    """

    result = {}

    if isinstance(data, dict):

        for key, value in data.items():

            new_key = f'{parent_key}_{key}' if parent_key else key

            if isinstance(value, dict):
                result.update(
                    flatten_dict(value, new_key)
                )

            elif isinstance(value, list):

                # list 裡面是 dictionary
                for i, item in enumerate(value):

                    if isinstance(item, dict):
                        result.update(
                            flatten_dict(
                                item,
                                f'{new_key}_{i}'
                            )
                        )
                    else:
                        result[f'{new_key}_{i}'] = item

            else:
                result[new_key] = value

    else:
        result[parent_key] = data

    return result

def get_nested_value(data, path):
    value = data

    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)

    return value

def get_value(data, key):
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for value in data.values():
            result = get_value(value, key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for value in data:
            result = get_value(value, key)
            if result is not None:
                return result

    return None

def decimal_value(value):
    if value in (None, '', '-99', '-99.0'):
        return None
    return value

def uploads3(filepath,filename):
    s3=boto3.client('s3')
    bucket_name = "shahowbackup"
    s3_object_key = "scraper/"+filename
    s3.upload_file(filepath, bucket_name, s3_object_key)    
    print("File uploaded successfully!")

def save_txt(url, file_path):
    response = requests.get(url, headers=headers)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(response.text)

def save_page(url, file_path):
    response = requests.get(url, headers=headers)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(response.text)

"""
url1 = 'https://tw.news.yahoo.com/'
url4 = 'https://tw.stock.yahoo.com/'

newsurl = r'C:/news/yahoo_news_{0}.html'. format(datetime.now().strftime('%Y%m%d'))
stocksurl = r'C:/news/yahoo_stock_{0}.html'. format(datetime.now().strftime('%Y%m%d'))

newsfilename =r'yahoo_news_{0}.html'. format(datetime.now().strftime('%Y%m%d'))
stockfilename =r'yahoo_stock_{0}.html'. format(datetime.now().strftime('%Y%m%d'))

#save_page(url1, newsurl)
#save_page(url4,stocksurl)

#uploads3(newsurl,newsfilename)
#uploads3(stocksurl,stockfilename)
"""

def save_weather_data_to_snowflake(connection, call_id):
    load_dotenv( dotenv_path=r"C:\Users\User\gmap_test\.env")
    account = os.getenv("CWA_APIKEY")
    url = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001'
    params = {    'Authorization': account,
    'format': 'JSON',
    'locationName': '中壢',
    'elementName': 'WeatherElement'
    }
    params['StationId'] = [
    # 署屬有人站
    "467490",

    # 署屬自動站
    "C0F0A0",
    "C0F0B0",
    "C0F0C0",
    "C0F0D0",
    "C0F0E0",
    "C0F850",
    "C0F970",
    "C0F9I0",
    "C0F9K0",
    "C0F9L0",
    "C0F9M0",
    "C0F9N0",
    "C0F9O0",
    "C0F9P0",
    "C0F9Q0",
    "C0F9R0",
    "C0F9S0",
    "C0F9T0",
    "C0F9U0",
    "C0F9V0",
    "C0F9X0",
    "C0F9Y0",
    "C0F9Z0",
    "C0FA10",
    "C0FA20",
    "C0FA30",
    "C0FA40",
    "C0FA50",
    "C0FA60",
    "C0FA70",
    "C0FA80",
    "C0FA90",
    "C0FB00",
    "C0FB10",
    "C0FB20",
    "C0FB30",
    "C0FB40",
    "C0FB70",

    # 農業站
    "C2F000",
    "C2F860",
    "C2F930",
    "C2F990",
    "C2F9A0",
    "C2FA00",
    "C2FB50",
    "C2FB60",
    "G2F820",
    "K2F750",
    ]
# 發送 GET 請求
    response = requests.get(url, params=params,verify=False, headers=headers)
    data = response.json()

    fields = data['result']['fields']
    locations = data['records']['Station']

    field_paths = {
    'StationName': ('StationName',),
    'StationId': ('StationId',),
    'StationAltitude': ('GeoInfo', 'StationAltitude'),
    'CountyName': ('GeoInfo', 'CountyName'),
    'TownName': ('GeoInfo', 'TownName'),
    'CountyCode': ('GeoInfo', 'CountyCode'),
    'TownCode': ('GeoInfo', 'TownCode'),
    'Weather': ('WeatherElement', 'Weather'),
    'Precipitation': ('WeatherElement', 'Now', 'Precipitation'),
    'WindDirection': ('WeatherElement', 'WindDirection'),
    'WindSpeed': ('WeatherElement', 'WindSpeed'),
    'AirTemperature': ('WeatherElement', 'AirTemperature'),
    'RelativeHumidity': ('WeatherElement', 'RelativeHumidity'),
    'AirPressure': ('WeatherElement', 'AirPressure'),
    'UVIndex': ('WeatherElement', 'UVIndex'),
    'PeakGustSpeed': ('WeatherElement', 'GustInfo', 'PeakGustSpeed'),
    'DateTime': ('ObsTime', 'DateTime'),
    }

    taichung_data = []
    for location in locations:
        print(location)
        record = {
        field['id']: get_nested_value(
            location,
            field_paths.get(field['id'], (field['id'],)),
        )
        for field in fields
    }
        record['StationLatitude'] = get_value(location, 'StationLatitude')
        record['StationLongitude'] = get_value(location, 'StationLongitude')
        taichung_data.append(record)
    station_insert_sql = """
INSERT INTO weather_station (
    station_id, station_name, latitude, longitude, station_altitude,
    county_name, town_name, county_code, town_code
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    station_name = VALUES(station_name),
    latitude = VALUES(latitude),
    longitude = VALUES(longitude),
    station_altitude = VALUES(station_altitude),
    county_name = VALUES(county_name),
    town_name = VALUES(town_name),
    county_code = VALUES(county_code),
    town_code = VALUES(town_code)
    """

    station_insert_sql = """
    INSERT INTO weather_station (
    station_id,
    station_name,
    latitude,
    longitude,
    station_altitude,
    county_name,
    town_name,
    county_code,
    town_code
   )VALUES ( %s, %s,    %s,    %s,    %s,    %s,    %s,%s,    %s );
    """
    
    observation_insert_sql = """
    INSERT INTO weather_observation (
    station_id, weather, precipitation, wind_direction, wind_speed,
    air_temperature, relative_humidity, air_pressure, uv_index,
    peak_gust_speed, observation_time,call_id)
      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
   
    """

    observation_rows = [
    (
        row['StationId'], row['Weather'], decimal_value(row['Precipitation']),
        decimal_value(row['WindDirection']), decimal_value(row['WindSpeed']),
        decimal_value(row['AirTemperature']), decimal_value(row['RelativeHumidity']),
        decimal_value(row['AirPressure']), decimal_value(row['UVIndex']),
        decimal_value(row['PeakGustSpeed']), row['DateTime'], call_id
    )
    for row in taichung_data
    ]

# Example with a MySQL connection:
    cursor = connection.cursor()
    station_select_sql = "SELECT station_id FROM weather_station"
    cursor.execute(station_select_sql)
    df =cursor.fetch_pandas_all()
    if df.empty:
        print("No existing stations found in the database.")
        existing_stations = set()
    else:
        existing_stations = set(df['station_id'.upper()].unique())
        
    for row in taichung_data:
        if row['StationId'] not in existing_stations:
            cursor.execute(station_insert_sql, (
                    row['StationId'], row['StationName'], row['StationLatitude'],
                    row['StationLongitude'], decimal_value(row['StationAltitude']),
                    row['CountyName'], row['TownName'], row['CountyCode'], row['TownCode']
                    ))
    
    cursor.executemany(observation_insert_sql, observation_rows)
    connection.commit()

load_dotenv( dotenv_path=r"C:\Users\User\gmap_test\.env")
account = os.getenv("SNOWFLAKE_ACCOUNT")
conn = sf.getConn()
call_id = str(uuid.uuid4())

save_weather_data_to_snowflake(conn, call_id)