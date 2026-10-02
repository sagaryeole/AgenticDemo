"""Draws the three test images used by agent28, so their correct answers are known exactly.

Run: uv run python agent28_multimodal/make_images.py      (the images are already in agent28_multimodal/images/)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "images"


def font(size: int):
    return ImageFont.load_default(size=size)


def shapes() -> None:
    """3 red circles, 2 blue squares, 1 green triangle."""
    img = Image.new("RGB", (600, 400), "white")
    d = ImageDraw.Draw(img)
    for x, y in [(60, 60), (260, 80), (470, 60)]:
        d.ellipse([x, y, x + 80, y + 80], fill="red")
    for x, y in [(90, 250), (380, 240)]:
        d.rectangle([x, y, x + 90, y + 90], fill="blue")
    d.polygon([(250, 340), (300, 240), (350, 340)], fill="green")
    img.save(OUT / "shapes.png")


def receipt() -> None:
    """A café receipt whose printed total is WRONG: the items add up to 10.25, the receipt says 11.25."""
    img = Image.new("RGB", (420, 420), "white")
    d = ImageDraw.Draw(img)
    d.text((110, 25), "CORNER CAFE", fill="black", font=font(32))
    lines = [("Coffee", "3.50"), ("Croissant", "2.75"), ("Orange juice", "4.00")]
    y = 110
    for item, price in lines:
        d.text((40, y), item, fill="black", font=font(26))
        d.text((300, y), price, fill="black", font=font(26))
        y += 50
    d.line([(40, y + 5), (380, y + 5)], fill="black", width=2)
    d.text((40, y + 25), "TOTAL", fill="black", font=font(28))
    d.text((300, y + 25), "11.25", fill="black", font=font(28))
    d.text((90, y + 110), "Thank you!", fill="black", font=font(24))
    img.save(OUT / "receipt.png")


def chart() -> None:
    """Library visitors per day: Mon 120, Tue 95, Wed 150, Thu 80, Fri 135 (total 580, busiest Wednesday)."""
    data = [("Mon", 120), ("Tue", 95), ("Wed", 150), ("Thu", 80), ("Fri", 135)]
    img = Image.new("RGB", (640, 420), "white")
    d = ImageDraw.Draw(img)
    d.text((150, 15), "Library visitors per day", fill="black", font=font(26))
    base, scale = 360, 1.7
    for i, (day, value) in enumerate(data):
        x = 70 + i * 110
        d.rectangle([x, base - value * scale, x + 70, base], fill="steelblue")
        d.text((x + 12, base - value * scale - 30), str(value), fill="black", font=font(22))
        d.text((x + 15, base + 10), day, fill="black", font=font(22))
    d.line([(50, base), (610, base)], fill="black", width=2)
    img.save(OUT / "chart.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    shapes()
    receipt()
    chart()
    print("wrote", sorted(p.name for p in OUT.iterdir()))
