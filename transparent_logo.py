"""
make_logo_transparent.py -- Run once: removes the white background from asik_logo.png
Requires: pip install pillow
"""
from PIL import Image

SRC = "asik_logo.png"
DST = "asik_logo_transparent.png"

img = Image.open(SRC).convert("RGBA")
pixels = img.getdata()

new_pixels = []
for r, g, b, a in pixels:
    # Any pixel that is near-white becomes fully transparent
    if r > 235 and g > 235 and b > 235:
        new_pixels.append((255, 255, 255, 0))
    else:
        new_pixels.append((r, g, b, a))

img.putdata(new_pixels)
img.save(DST, "PNG")
print(f"Saved transparent logo as {DST}")