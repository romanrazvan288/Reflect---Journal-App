import struct
import zlib
from pathlib import Path


def generate_png_and_ico(output_dir: Path):
    width, height = 256, 256
    raw_rows = bytearray()

    cx, cy = width / 2.0, height / 2.0
    r_outer = 110.0
    r_inner = 70.0

    # Color palette
    bg_r, bg_g, bg_b, bg_a = 0, 0, 0, 0
    fg_r, fg_g, fg_b, fg_a = 59, 142, 208, 255  # CustomTkinter blue
    sparkle_r, sparkle_g, sparkle_b = 255, 255, 255

    for y in range(height):
        raw_rows.append(0)  # filter type 0 (None)
        for x in range(width):
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist <= r_outer:
                # Base circle
                ratio = dist / r_outer
                cr = int(37 + (59 - 37) * (1 - ratio))
                cg = int(99 + (142 - 99) * (1 - ratio))
                cb = int(235 + (208 - 235) * (1 - ratio))
                alpha = 255
                if dist > r_outer - 2.0:
                    alpha = int(255 * (r_outer - dist) / 2.0)

                # Draw an open book / quill or sparkling reflection in the center
                # Simple geometric notebook / journal motif:
                # Vertical spine around dx = 0, pages left and right
                if abs(dx) < 60 and abs(dy) < 55:
                    if abs(dx) > 4 and dy > -45 and dy < 45:
                        # Pages
                        cr, cg, cb = 241, 245, 249
                        # Add lines on the page
                        if int(dy) in (-20, -5, 10, 25) and abs(dx) < 45:
                            cr, cg, cb = 148, 163, 184
                    elif abs(dx) <= 4:
                        # Spine
                        cr, cg, cb = 30, 41, 59

                raw_rows.extend([cr, cg, cb, alpha])
            else:
                raw_rows.extend([bg_r, bg_g, bg_b, bg_a])

    def chunk(tag: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return length + tag + data + crc

    # PNG chunks
    header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)
    idat = chunk(b"IDAT", zlib.compress(bytes(raw_rows), 9))
    iend = chunk(b"IEND", b"")
    png_bytes = header + ihdr + idat + iend

    png_path = output_dir / "icon.png"
    png_path.write_bytes(png_bytes)

    # Windows ICO format containing standard PNG payload
    # ICONDIR header: 3 WORDs -> reserved (0), type (1 for icon), count (1)
    icondir = struct.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY:
    # bWidth (0 means 256), bHeight (0 means 256), bColorCount (0), bReserved (0),
    # wPlanes (1), wBitCount (32), dwBytesInRes (len(png_bytes)), dwImageOffset (6 + 16 = 22)
    direntry = struct.pack(
        "<BBBBHHII",
        0,  # width 256
        0,  # height 256
        0,  # color count
        0,  # reserved
        1,  # planes
        32,  # bpp
        len(png_bytes),
        22,  # offset
    )

    ico_bytes = icondir + direntry + png_bytes
    ico_path = output_dir / "icon.ico"
    ico_path.write_bytes(ico_bytes)


if __name__ == "__main__":
    generate_png_and_ico(Path(__file__).resolve().parent)
