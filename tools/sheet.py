"""sheet.py OUT.png IMG [IMG ...]: side-by-side contact sheet with the iOS squircle-ish mask."""
import sys
from PIL import Image, ImageDraw

out, imgs = sys.argv[1], sys.argv[2:]
size, pad = 300, 20
mask = Image.new("L", (1024, 1024), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, 1023, 1023], radius=230, fill=255)
sheet = Image.new("RGB", (pad + len(imgs) * (size + pad), size + 2 * pad), (200, 200, 205))
for i, p in enumerate(imgs):
    im = Image.open(p).convert("RGBA").resize((1024, 1024), Image.LANCZOS)
    tile = Image.new("RGB", (1024, 1024), (200, 200, 205))
    tile.paste(im, (0, 0), Image.composite(im.getchannel("A"), Image.new("L", (1024, 1024), 0), mask))
    sheet.paste(tile.resize((size, size), Image.LANCZOS), (pad + i * (size + pad), pad))
sheet.save(out)
