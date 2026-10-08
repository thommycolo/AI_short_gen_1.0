"""Script to generate default native assets (icon and splash)."""

from pathlib import Path
from PIL import Image, ImageDraw

Path("assets/icons").mkdir(parents=True, exist_ok=True)

# Create 256x256 app icon
img = Image.new('RGBA', (256, 256), (24, 26, 32, 255))
d = ImageDraw.Draw(img)
d.rounded_rectangle([16, 16, 240, 240], radius=40, fill=(33, 36, 44, 255), outline=(107, 130, 166, 255), width=6)
d.polygon([(100, 75), (185, 128), (100, 181)], fill=(191, 161, 117, 255))
img.save('assets/icons/app.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])

# Create splash.png
splash = Image.new('RGBA', (600, 350), (24, 26, 32, 255))
sd = ImageDraw.Draw(splash)
sd.rounded_rectangle([10, 10, 590, 340], radius=16, fill=(33, 36, 44, 255), outline=(52, 57, 70, 255), width=2)
sd.polygon([(260, 120), (340, 165), (260, 210)], fill=(191, 161, 117, 255))
splash.save('assets/splash.png')

print('Icon and splash generated successfully!')

