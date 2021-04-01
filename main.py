import os
import sys
import gc
import time
import board
import json
import adafruit_pyportal
import adafruit_datetime as datetime
import adafruit_requests as requests

from secrets import secrets

wifi = adafruit_pyportal.wifi.WiFi(status_neopixel=board.NEOPIXEL)
wifi.connect(secrets["wifi"]["ssid"], secrets["wifi"]["password"])

url = "https://" + secrets["api"]["host"] + "/v1/objects/services?filter=service.state!=0&attrs=state&attrs=last_hard_state_change"
headers = {
    "Authorization": "Basic " + secrets["api"]["credentials"]
}

states = ["OK", "WARNING", "CRITICAL", "UNKNOWN"]
cached = ""

while True:
    response = wifi.requests.get(url, headers=headers)
    if cached != response.text:
        cached = response.text

        print("-" * 40)

        if response.status_code == 200:
            data = json.loads(cached)
            for service in data["results"]:
                bits = service["name"].split("!")
                host = bits[0]
                name = bits[1]
                attrs = service["attrs"]
                state = int(attrs["state"])
                last_hard_state_change = int(attrs["last_hard_state_change"])
                last_hard_state_change_date = datetime.datetime.fromtimestamp(last_hard_state_change)

                print(name, " @ ", host)
                print(states[state], " since ", last_hard_state_change_date.isoformat())
        else:
            print("ERROR: ", response.text)

        print("-" * 40)

    response.close()

    time.sleep(5)