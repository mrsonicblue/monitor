import os
import sys
import gc
import time
import tzutil
import board
import displayio
import terminalio
import json
import adafruit_pyportal
import adafruit_requests as requests
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.label import Label
import render_bdf

from secrets import secrets

def clear():
    for r in range(21):
        print("")

def hour_to_12(h):
    if h == 0:
        return 12
    if h > 12:
        return h - 12
    return h

def hour_to_suffix(h):
    if h < 12:
        return "AM"
    return "PM"

def format_time(t):
    return "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d} {}".format(
        t.tm_year,
        t.tm_mon,
        t.tm_mday,
        hour_to_12(t.tm_hour),
        t.tm_min,
        t.tm_sec,
        hour_to_suffix(t.tm_hour),
    )

def render_text(grid, maps, text):
    xs = 66
    ys = 1
    ts = len(text)
    i = 0
    map = 0
    for y in range(ys):
        for x in range(xs):
            if i < ts:
                while True:
                    c = ord(text[i])
                    i += 1
                    if c > 10:
                        break
                    map = c

                if c in maps[map]:
                    grid[x, y] = maps[map][c]
                else:
                    grid[x, y] = 0
            else:
                grid[x, y] = 0


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
maps = [normal_map, bold_map]

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

url = "https://" + secrets["api"]["host"] + "/v1/objects/services?filter=service.state!=0%26%26service.state_type==1&attrs=state&attrs=last_hard_state_change"
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

                    if last_hard_state_change > 0:
                        since = format_time(tzutil.US_Central.localtime(last_hard_state_change))
                    else:
                        since = "NEVER"

                    block[BLOCK_BULLET].fill = STATE_COLORS[state]
                    top_text = "\1" + name + "\0 " + host
                    bottom_text = STATE_LABELS[state] + " since " + since

                    render_text(block[BLOCK_TOP], maps, top_text)
                    render_text(block[BLOCK_BOTTOM], maps, bottom_text)

                    if blocks[i] not in root:
                        root.append(blocks[i])
                else:
                    if blocks[i] in root:
                        root.remove(blocks[i])

                i += 1
            
            diff = service_count - len(blocks)
            diff_text = "" if (diff <= 0) else "and " + str(diff) + " more..."
            render_text(andthen_label, maps, diff_text)
        else:
            print("ERROR: ", response.text)

    response.close()

    gc.collect()

    time.sleep(30)