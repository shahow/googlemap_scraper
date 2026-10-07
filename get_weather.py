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
    acc=sf.load_aws_secrets("CWA_APIKEY")
    account = acc.get("CWA_APIKEY")

    url = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001'
    params = {    'Authorization': account,
    'format': 'JSON',
    'locationName': '中壢',
    'elementName': 'WeatherElement'
    }

    taipei_stations = [
    "466910",  # 鞍部
    "466920",  # 臺北
    "466930",  # 竹子湖
    "C0A770",  # 科教館
    "C0A980",  # 社子
    "C0A9C0",  # 天母
    "C0A9F0",  # 內湖
    "C0AC40",  # 大屯山
    "C0AC70",  # 信義
    "C0AC80",  # 文山
    "C0AH40",  # 平等
    "C0AH70",  # 松山
    "C0AI40",  # 石牌
            
            ]

    new_taipei_stations = [
    "466881",  # 新北
    "466900",  # 淡水
    "C0A520",  # 山佳
    "C0A530",  # 坪林
    "C0A550",  # 泰平
    "C0A570",  # 桶後
    "C0A640",  # 石碇
    "C0A860",  # 大坪
    "C0A870",  # 五指山
    "C0A890",  # 雙溪
    "C0A931",  # 三和
    "C0A940",  # 金山
    "C0A950",  # 鼻頭角
    "C0A970",  # 三貂角
    "C0AC60",  # 三峽
    "C0ACA0",  # 新莊
    "C0AD10",  # 八里
    "C0AD30",  # 蘆洲
    "C0AD40",  # 土城
    "C0AD50",  # 鶯歌
    "C0AG80",  # 中和
    "C0AH00",  # 汐止
    "C0AH10",  # 永和
    "C0AH30",  # 五分山
    "C0AH50",  # 林口
    "C0AH80",  # 深坑
    "C0AH90",  # 福山植物園
    "C0AI00",  # 五股
    "C0AI10",  # 屈尺
    "C0AI20",  # 白沙灣
    "C0AI30",  # 三重
    "C0AJ20",  # 野柳
    "C0AJ30",  # 淡水觀海
    "C0AJ40",  # 石門
    "C0AJ50",  # 水湳洞
    "C0AJ60",  # 六塊厝
    "C0AJ70",  # 田寮
    "C0AJ80",  # 板橋
    "C0AJ90",  # 澳底
    "C0AK10",  # 太平里
    "C0AK30",  # 硬漢嶺
]

    keelung_stations = [
    "466940",  # 基隆
    "466950",  # 彭佳嶼
    "C0B010",  # 七堵
    "C0B020",  # 基隆嶼
    "C0B040",  # 大武崙
    "C0B050",  # 八斗子
    "C0B060",  # 暖暖
]



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

    params['StationId'] = params['StationId'] + taipei_stations + new_taipei_stations + keelung_stations
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

if __name__ == "__main__":
    conn = sf.getConn()
    call_id = str(uuid.uuid4())
    try:
        save_weather_data_to_snowflake(conn, call_id)
    finally:
        conn.close()
