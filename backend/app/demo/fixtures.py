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


def make_complex_invoice(path: Path) -> None:
    """Marketplace-style invoice: two columns, line-item table, Rs symbols, dd.mm.yyyy, amount in words."""
    img = Image.new("RGB", (900, 700), "white")
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, 900, 50], fill=(200, 30, 30))
    dr.text((20, 10), BANNER, fill="white", font=_font(28))
    f, b = _font(15), _font(17)
    dr.text((470, 70), "Tax Invoice/Bill of Supply/Cash Memo", fill="black", font=b)
    dr.text((20, 120), "Sold By:", fill="black", font=b)
    dr.text((20, 145), "Fake Mart Private Limited\nSample Street 1, Test City, 560001\nIN", fill="black", font=f)
    dr.text((560, 120), "Billing Address:", fill="black", font=b)
    dr.text((560, 145), "Test Customer\n12 Demo Lane, Test City", fill="black", font=f)
    dr.text((20, 240), "GST Registration No: 29AAAAA0000A1Z5", fill="black", font=b)
    dr.text((20, 300), "Order Number: 000-1234567-7654321", fill="black", font=b)
    dr.text((20, 325), "Order Date: 30.03.2026", fill="black", font=b)
    dr.text((470, 300), "Invoice Number: FAKE-7547", fill="black", font=b)
    dr.text((470, 325), "Invoice Details: KA-FAKE-143189331", fill="black", font=b)
    dr.text((470, 350), "Invoice Date: 30.03.2026", fill="black", font=b)
    dr.rectangle([20, 400, 880, 560], outline="black")
    dr.text((28, 408), "Sl.   Description                                   Unit Price  Qty  Net Amount  Tax Rate  Tax Amount  Total Amount", fill="black", font=_font(12))
    dr.text((28, 440), "1     Aurora A5 (Midnight/Black) | B0FAKE1234 ( Aurora A5 (Midnight/Black) )", fill="black", font=f)
    dr.text((60, 462), "HSN:8517", fill="black", font=f)
    dr.text((560, 462), "₹21,428.57   1   ₹21,428.57   12%   ₹2,571.43   ₹24,000.00", fill="black", font=_font(13))
    dr.text((28, 530), "TOTAL:                                                     ₹2,571.43    ₹24,000.00", fill="black", font=b)
    dr.text((20, 580), "Amount in Words:", fill="black", font=b)
    dr.text((20, 605), "Twenty Four Thousand only", fill="black", font=b)
    dr.text((560, 650), "Authorized Signatory", fill="black", font=f)
    img.save(path)


def ensure_fixtures() -> Path:
    FIXTURE_DIR.mkdir(exist_ok=True)
    if not (FIXTURE_DIR / "complex_marketplace_invoice.png").exists():
        make_complex_invoice(FIXTURE_DIR / "complex_marketplace_invoice.png")
    for name, (title, lines) in SPECS.items():
        if not (FIXTURE_DIR / name).exists():
            make_image(FIXTURE_DIR / name, title, lines)
    for name, text in TXT.items():
        if not (FIXTURE_DIR / name).exists():
            (FIXTURE_DIR / name).write_text(text, encoding="utf-8")
    return FIXTURE_DIR


if __name__ == "__main__":
    print(ensure_fixtures())
