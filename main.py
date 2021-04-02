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
import render_bdf

from secrets import secrets

def clear():
    for r in range(21):
        print("")

def render_text(grid, map, text):
    xs = 66
    ys = 1
    ts = len(text)
    i = 0
    for y in range(ys):
        for x in range(xs):
            if i < ts:
                c = ord(text[i])
                if c in map:
                    grid[x, y] = map[c]
                else:
                    grid[x, y] = 0
            else:
                grid[x, y] = 0
            i += 1


clear()
print("Connecting to wifi")

wifi = adafruit_pyportal.wifi.WiFi(status_neopixel=board.NEOPIXEL)
wifi.connect(secrets["wifi"]["ssid"], secrets["wifi"]["password"])

print("Starting up")

BLACK = 0x000000
DGREY = 0x888888
LGREY = 0xAAAAAA
WHITE = 0xFFFFFF
STATE_COLORS = [0x23BD7D, 0xFFA856, 0xFF4C68, 0xB33AF6]
STATE_LABELS = ["OK", "WARNING", "CRITICAL", "UNKNOWN"]

palette_white = displayio.Palette(2)
palette_white[0] = BLACK
palette_white[1] = WHITE

palette_grey = displayio.Palette(2)
palette_grey[0] = BLACK
palette_grey[1] = LGREY

TILE_COUNT = 160
TILE_WIDTH = 7
TILE_HEIGHT = 13
tiles = displayio.Bitmap(TILE_COUNT * TILE_WIDTH, TILE_HEIGHT, 2)

glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.:/! '
normal_map = render_bdf.render_bdf("/fonts/ctrld-fixed-13r.bdf", glyphs, tiles, TILE_WIDTH, TILE_HEIGHT, 1)
bold_map = render_bdf.render_bdf("/fonts/ctrld-fixed-13b.bdf", glyphs, tiles, TILE_WIDTH, TILE_HEIGHT, len(normal_map) + 1)

display = board.DISPLAY

root = displayio.Group(max_size=15)
display.show(root)

blocks = []
BLOCK_BULLET = 0
BLOCK_TOP = 1
BLOCK_BOTTOM = 2
for i in range(10):
    block = displayio.Group(max_size=5, x=0, y=31 * i)
    blocks.append(block)

    bullet = Rect(0, 0, 10, 26, fill=WHITE)
    block.append(bullet)

    top_label = displayio.TileGrid(tiles, pixel_shader=palette_white, x=14, y=0, width=66, height=1, tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT)
    block.append(top_label)

    bottom_label = displayio.TileGrid(tiles, pixel_shader=palette_grey, x=14, y=13, width=66, height=1, tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT)
    block.append(bottom_label)

andthen = displayio.Group(max_size=10, x=0, y=307)
root.append(andthen)

andthen_label = displayio.TileGrid(tiles, pixel_shader=palette_white, x=14, y=0, width=66, height=1, tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT)
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

                    top_text = name + " - " + host
                    bottom_text = STATE_LABELS[state] + " since " + last_hard_state_change_date.isoformat()

                    render_text(block[BLOCK_TOP], bold_map, top_text)
                    render_text(block[BLOCK_BOTTOM], normal_map, bottom_text)

                    if blocks[i] not in root:
                        root.append(blocks[i])
                else:
                    if blocks[i] in root:
                        root.remove(blocks[i])

                i += 1
            
            diff = service_count - len(blocks)
            diff_text = "" if (diff < 0) else "and " + str(diff) + " more..."
            render_text(andthen_label, normal_map, diff_text)

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

    gc.collect()

    time.sleep(30)