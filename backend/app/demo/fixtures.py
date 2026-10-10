"""Generate synthetic demo documents. Every image is stamped FAKE - SYNTHETIC DEMO DOCUMENT."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import ROOT

FIXTURE_DIR = ROOT / "demo_fixtures"
BANNER = "FAKE - SYNTHETIC DEMO DOCUMENT"
_FONTS = [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def _font(size: int):
    for f in _FONTS:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_image(path: Path, title: str, lines: list[str]) -> None:
    img = Image.new("RGB", (1400, 220 + 80 * (len(lines) + 1)), "white")
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, 1400, 90], fill=(200, 30, 30))
    dr.text((40, 18), BANNER, fill="white", font=_font(46))
    dr.text((40, 120), title, fill="black", font=_font(40))
    y = 220
    for ln in lines:
        dr.text((40, y), ln, fill="black", font=_font(36))
        y += 80
    img.save(path)


SPECS = {
    "cp001_invoice.png": ("Purchase Invoice (Synthetic Store)", [
        "Product Model: Northstar N14", "Serial Number: NS-N14-000123",
        "Purchase Date: 2026-06-01", "Total Amount: INR 65000.00"]),
    "cp003_invoice.png": ("Purchase Invoice (Synthetic Store)", [
        "Product Model: Northstar N14", "Serial Number: NS-N14-000789",
        "Purchase Date: 2026-03-15", "Total Amount: INR 62000.00"]),
    "cp004_invoice.png": ("Purchase Invoice (Synthetic Store)", [
        "Product Model: Aurora A5", "IMEI: 356938035643809",
        "Purchase Date: 2026-07-01", "Total Amount: INR 24000.00"]),
    "cp004_repair_receipt.png": ("Repair Receipt (Synthetic Service Centre)", [
        "Product Model: Aurora A5", "IMEI: 356938035643809",
        "Repair Date: 2026-09-29", "Total Amount: INR 9800.00", "Description: Replaced cracked display"]),
}
TXT = {
    "cp002_statement.txt": "FAKE - SYNTHETIC DEMO DOCUMENT\nCustomer Statement\nIncident Date: 2026-10-02\n"
                          "Description: Laptop slipped from desk and the screen cracked.\n",
}


def ensure_fixtures() -> Path:
    FIXTURE_DIR.mkdir(exist_ok=True)
    for name, (title, lines) in SPECS.items():
        if not (FIXTURE_DIR / name).exists():
            make_image(FIXTURE_DIR / name, title, lines)
    for name, text in TXT.items():
        if not (FIXTURE_DIR / name).exists():
            (FIXTURE_DIR / name).write_text(text, encoding="utf-8")
    return FIXTURE_DIR


if __name__ == "__main__":
    print(ensure_fixtures())
