import struct
import zlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
png_path = BASE_DIR / "icon.png"
ico_path = BASE_DIR / "icon.ico"

# 1. Generate icon.png (256x256 RGBA)
width, height = 256, 256
raw_rows = bytearray()
cx, cy = width / 2.0, height / 2.0
r_outer = 112.0

for y in range(height):
    raw_rows.append(0)  # filter type 0 (None)
    for x in range(width):
        dx = x - cx
        dy = y - cy
        dist = (dx * dx + dy * dy) ** 0.5

        if dist <= r_outer:
            ratio = dist / r_outer
            cr = int(37 + (59 - 37) * (1 - ratio))
            cg = int(99 + (142 - 99) * (1 - ratio))
            cb = int(235 + (208 - 235) * (1 - ratio))
            alpha = 255
            if dist > r_outer - 2.0:
                alpha = int(255 * (r_outer - dist) / 2.0)

            # Open notebook / reflection pages motif
            if abs(dx) < 64 and abs(dy) < 56:
                if abs(dx) > 4 and dy > -46 and dy < 46:
                    cr, cg, cb = 241, 245, 249
                    if int(dy) in (-22, -7, 8, 23) and abs(dx) < 50:
                        cr, cg, cb = 148, 163, 184
                elif abs(dx) <= 4:
                    cr, cg, cb = 30, 41, 59

            raw_rows.extend([cr, cg, cb, alpha])
        else:
            raw_rows.extend([0, 0, 0, 0])

def chunk(tag: bytes, data: bytes) -> bytes:
    length = struct.pack(">I", len(data))
    crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return length + tag + data + crc

header = b"\x89PNG\r\n\x1a\n"
ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
ihdr = chunk(b"IHDR", ihdr_data)
idat = chunk(b"IDAT", zlib.compress(bytes(raw_rows), 9))
iend = chunk(b"IEND", b"")
png_bytes = header + ihdr + idat + iend

png_path.write_bytes(png_bytes)

# 2. Generate icon.ico (standard ICO container housing the PNG)
icondir = struct.pack("<HHH", 0, 1, 1)
direntry = struct.pack(
    "<BBBBHHII",
    0, 0, 0, 0, 1, 32, len(png_bytes), 22
)
ico_bytes = icondir + direntry + png_bytes
ico_path.write_bytes(ico_bytes)

# 3. Create ~/.local/share/applications/reflect.desktop
desktop_dir = Path.home() / ".local" / "share" / "applications"
desktop_dir.mkdir(parents=True, exist_ok=True)
desktop_file = desktop_dir / "reflect.desktop"

desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Reflect
Comment=Personal Journal Desktop App
Exec=python3 "{BASE_DIR / 'app.py'}"
Icon={png_path}
Terminal=false
Categories=Utility;Office;
StartupWMClass=reflect
"""

desktop_file.write_text(desktop_content, encoding="utf-8")
desktop_file.chmod(0o755)
print("Setup completed successfully.")
