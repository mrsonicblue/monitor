import gc
import displayio

def render_bdf(filename, code_points, bmp, tile_width, tile_height, tile_index):
    metadata = True
    character = False
    code_point = None
    bytes_per_row = 1
    desired_character = False
    current_info = {}
    current_y = 0
    rounded_x = 1
    remaining = set(code_points)
    bmp_width = bmp.width
    bmp_height = bmp.height

    map = {}

    file = open(filename, "rb")
    
    line = file.readline()
    line = str(line, "utf-8")
    if not line or not line.startswith("STARTFONT 2.1"):
        raise ValueError("Unsupported file version")
    
    file.seek(0)
    while True:
        line = file.readline()
        if not line:
            break
        if line.startswith(b"CHARS "):
            metadata = False
        elif line.startswith(b"SIZE"):
            _, point_size, x_resolution, y_resolution = line.split()
        elif line.startswith(b"COMMENT"):
            pass
        elif line.startswith(b"STARTCHAR"):
            # print(lineno, line.strip())
            # _, character_name = line.split()
            character = True
        elif line.startswith(b"ENDCHAR"):
            character = False
            if desired_character:
                bounds = current_info["bounds"]
                shift = current_info["shift"]
                gc.collect()
                map[code_point] = tile_index
                remaining.remove(code_point)
                tile_index += 1
                if not remaining:
                    break
            desired_character = False
        elif line.startswith(b"BBX"):
            if desired_character:
                _, x, y, x_offset, y_offset = line.split()
                x = int(x)
                y = int(y)
                x_offset = int(x_offset)
                y_offset = int(y_offset)
                current_info["bounds"] = (x, y, x_offset, y_offset)
        elif line.startswith(b"BITMAP"):
            if desired_character:
                rounded_x = x // 8
                if x % 8 > 0:
                    rounded_x += 1
                bytes_per_row = rounded_x
                if bytes_per_row % 4 > 0:
                    bytes_per_row += 4 - bytes_per_row % 4
                current_y = 0
        elif line.startswith(b"ENCODING"):
            _, code_point = line.split()
            code_point = int(code_point)
            if code_point in remaining:
                desired_character = True
                current_info = {"bounds": None, "shift": None}
        elif line.startswith(b"DWIDTH"):
            if desired_character:
                _, shift_x, shift_y = line.split()
                shift_x = int(shift_x)
                shift_y = int(shift_y)
                current_info["shift"] = (shift_x, shift_y)
        elif line.startswith(b"SWIDTH"):
            pass
        elif character:
            if desired_character:
                bits = int(line.strip(), 16)
                width = current_info["bounds"][0]
                start = (current_y * bmp_width) + (tile_width * tile_index)
                x = 0
                for i in range(rounded_x):
                    val = (bits >> ((rounded_x - i - 1) * 8)) & 0xFF
                    for j in range(7, -1, -1):
                        if x >= width:
                            break
                        bit = 0
                        if val & (1 << j) != 0:
                            bit = 1
                        bmp[start + x] = bit
                        x += 1
                current_y += 1
        elif metadata:
            # print(lineno, line.strip())
            pass

    file.close()

    return map