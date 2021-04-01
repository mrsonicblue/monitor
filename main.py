import os
import sys
import gc
import time
import board
import displayio
import terminalio
import json
import adafruit_pyportal
import adafruit_datetime as datetime
import adafruit_requests as requests
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.label import Label

from secrets import secrets

WHITE = 0xFFFFFF
GREY = 0x888888
BLACK = 0x000000
BUTTON1 = 0x3D1810
BUTTON2 = 0x7F3122
STATES = ["OK", "WARNING", "CRITICAL", "UNKNOWN"]
STATE_COLORS = [0x23BD7D, 0xFFA856, 0xFF4C68, 0xB33AF6]

def clear():
    for r in range(21):
        print("")

clear()
print("Connecting to wifi")

wifi = adafruit_pyportal.wifi.WiFi(status_neopixel=board.NEOPIXEL)
wifi.connect(secrets["wifi"]["ssid"], secrets["wifi"]["password"])

print("Starting up")

display = board.DISPLAY

root = displayio.Group(max_size=15)
display.show(root)

normal_font = terminalio.FONT
bold_font = terminalio.FONT

# normal_font = bitmap_font.load_font("/fonts/ctrld-fixed-13r.bdf")
# normal_font.load_glyphs(b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.:/! ')

# bold_font = bitmap_font.load_font("/fonts/ctrld-fixed-13b.bdf")
# bold_font.load_glyphs(b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.:/! ')

blocks = []
BLOCK_BULLET = 0
BLOCK_TOP = 1
BLOCK_BOTTOM = 2
for i in range(10):
    y = 31 * i
    
    block = displayio.Group(max_size=5)
    blocks.append(block)

    bullet = Rect(0, y, 10, 26, fill=WHITE)
    block.append(bullet)

    top_label = Label(bold_font, text="blah blah on blah", max_glyphs=50, x=14, y=y + 6, color=WHITE)
    block.append(top_label)

    # bottom_label = Label(normal_font, text="01/04/2021 12:12 PM", max_glyphs=19, x=14, y=y + 18, color=GREY)
    # block.append(bottom_label)

andthen = displayio.Group(max_size=10)
root.append(andthen)

andthen_label = Label(normal_font, text="", max_glyphs=25, x=0, y=314, color=WHITE)
andthen.append(andthen_label)

url = "https://" + secrets["api"]["host"] + "/v1/objects/services?filter=service.state!=0&attrs=state&attrs=last_hard_state_change"
headers = {
    "Authorization": "Basic " + secrets["api"]["credentials"]
}

cached = ""
while True:
    response = wifi.requests.get(url, headers=headers)
    if cached != response.text:
        cached = response.text

        clear()

        if response.status_code == 200:
            data = json.loads(cached)
            services = data["results"]
            service_count = len(services)
            
            i = 0
            for block in blocks:
                if service_count > i:
                    service = services[i]
                    bits = service["name"].split("!")
                    host = bits[0]
                    name = bits[1]
                    attrs = service["attrs"]
                    state = int(attrs["state"])
                    last_hard_state_change = int(attrs["last_hard_state_change"])
                    last_hard_state_change_date = datetime.datetime.fromtimestamp(last_hard_state_change)

                    block[BLOCK_BULLET].fill = STATE_COLORS[state]
                    block[BLOCK_TOP].text = (name + " @ " + host)[:50]

                    if blocks[i] not in root:
                        root.append(blocks[i])
                else:
                    if blocks[i] in root:
                        root.remove(blocks[i])

                i = i + 1
            
            diff = service_count - len(blocks)
            if diff > 0:
                andthen_label.text = "and " + str(diff) + " more..."
            else:
                andthen_label.text = ""

            # for service in data["results"]:
            #     bits = service["name"].split("!")
            #     host = bits[0]
            #     name = bits[1]
            #     attrs = service["attrs"]
            #     state = int(attrs["state"])
            #     last_hard_state_change = int(attrs["last_hard_state_change"])
            #     last_hard_state_change_date = datetime.datetime.fromtimestamp(last_hard_state_change)

            #     print(name, " @ ", host)
            #     print(STATES[state], " since ", last_hard_state_change_date.isoformat())
        else:
            print("ERROR: ", response.text)

    response.close()

    time.sleep(30)