import json
import requests
from schedule import every, repeat, run_pending
from datetime import datetime
import time

@repeat(every(10).minutes)
def get_traffic_data():
    url = "	https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=501b4858-8078-4508-9a50-368789a1a2a7"
    response = requests.get(url,verify=False)
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=4))
    print(len(data))

while True:
    run_pending()
    time.sleep(60)