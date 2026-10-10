"""Generate synthetic demo documents. Every image is stamped FAKE - SYNTHETIC DEMO DOCUMENT.

Documents imitate real-world layouts (shop GST invoices with item tables and IMEI lines, marketplace invoices,
service receipts) because the point of the demo is to show the reader coping with messy documents.
All names, shops, numbers and devices are invented.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import ROOT

FIXTURE_DIR = ROOT / "demo_fixtures"
FIXTURE_VERSION = "3"  # bump to regenerate every file
BANNER = "FAKE - SYNTHETIC DEMO DOCUMENT"
INK, BLUE, RED, GREY = (20, 20, 20), (28, 74, 150), (190, 30, 30), (90, 90, 90)
_REG = [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
_BOLD = [r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def _font(size: int, bold: bool = False):
    for f in (_BOLD if bold else _REG):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ------------------------------------------------------------------ number formatting
def inr(value: Decimal | int | float, symbol: str = "") -> str:
    """Indian digit grouping: 214760 -> 2,14,760.00"""
    d = Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    whole, frac = f"{abs(d):.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return f"{symbol}{','.join(groups + [tail])}.{frac}" if groups else f"{symbol}{tail}.{frac}"


_ONES = ("Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen Fifteen Sixteen "
         "Seventeen Eighteen Nineteen").split()
_TENS = "_ _ Twenty Thirty Forty Fifty Sixty Seventy Eighty Ninety".split()


def _below_100(n: int) -> str:
    return _ONES[n] if n < 20 else _TENS[n // 10] + (f" {_ONES[n % 10]}" if n % 10 else "")


def words(n: int) -> str:
    """Indian-style number words: 214760 -> Two Lakh Fourteen Thousand Seven Hundred And Sixty"""
    parts: list[str] = []
    for unit, label in ((10_000_000, "Crore"), (100_000, "Lakh"), (1_000, "Thousand")):
        if n >= unit:
            parts.append(f"{words(n // unit)} {label}")
            n %= unit
    if n >= 100:
        parts.append(f"{_ONES[n // 100]} Hundred")
        n %= 100
    if n:
        parts.append(("And " if parts else "") + _below_100(n))
    return " ".join(parts)


# ------------------------------------------------------------------ drawing helpers
def _banner(dr: ImageDraw.ImageDraw, width: int) -> None:
    dr.rectangle([0, 0, width, 54], fill=RED)
    dr.text((width // 2, 27), BANNER, fill="white", font=_font(30, True), anchor="mm")


def _right(dr, x, y, text, font, fill=INK):
    dr.text((x, y), text, font=font, fill=fill, anchor="ra")


@dataclass
class Item:
    name: str
    total: Decimal               # price including GST, as shown to the customer
    sub: str | None = None       # e.g. "IMEI 356938035643809" or "Serial No: NS-N14-000123"
    hsn: str = "8517"
    qty: int = 1


def make_retail_invoice(path: Path, *, shop: str, tagline: str, address: tuple[str, str], phone: str, gstin: str,
                        inv_no: str, date_label: str, date_text: str, customer: str, place: str, items: list[Item],
                        words_label: str | None = "Total in words", subtotal_row: bool = False, gst_rate: int = 18,
                        bank: tuple[str, str, str] = ("Demo Bank", "Test Branch", "0000000000")) -> Decimal:
    """Shop-style GST tax invoice. Returns the grand total."""
    W, H = 1100, 1180 + 76 * len(items)
    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)
    _banner(dr, W)
    y = 76
    dr.text((46, y), shop, font=_font(46, True), fill=BLUE); y += 62
    for line in address:
        dr.text((46, y), line, font=_font(22), fill=INK); y += 28
    dr.text((46, y), f"Ph: {phone}", font=_font(22), fill=INK); y += 40
    dr.line((36, y, W - 36, y), fill=INK, width=2); y += 10
    dr.text((W // 2, y + 14), tagline, font=_font(20), fill=GREY, anchor="mm"); y += 40
    dr.line((36, y, W - 36, y), fill=INK, width=2); y += 14
    dr.text((46, y + 8), f"GSTIN : {gstin}", font=_font(28), fill=INK)
    dr.text((470, y + 4), "TAX INVOICE", font=_font(38, True), fill=BLUE)
    _right(dr, W - 46, y + 14, "ORIGINAL FOR RECIPIENT", _font(19, True)); y += 72

    top = y
    dr.rectangle([36, top, W - 36, top + 190], outline=BLUE, width=2)
    dr.line((520, top, 520, top + 190), fill=BLUE, width=2)
    dr.text((278, top + 14), "Customer Detail", font=_font(21, True), fill=INK, anchor="ma")
    for i, (k, v) in enumerate((("Name", customer), ("Address", place), ("PHONE", "-"), ("Place of Supply", place))):
        dr.text((52, top + 56 + i * 32), k, font=_font(20, True), fill=INK)
        dr.text((210, top + 56 + i * 32), v, font=_font(20), fill=INK)
    dr.text((540, top + 22), "Invoice No.", font=_font(21), fill=INK)
    dr.text((700, top + 22), inv_no, font=_font(21, True), fill=INK)
    dr.text((540, top + 62), date_label, font=_font(21), fill=INK)
    dr.text((700, top + 62), date_text, font=_font(21), fill=INK)
    y = top + 210

    cols = [36, 82, 392, 462, 520, 640, 770, 842, 940, W - 36]
    heads = ["Sr.", "Name of Product / Service", "HSN", "Qty", "Rate", "Taxable Value", f"GST %", "GST Amt", "Total"]
    dr.rectangle([cols[0], y, cols[-1], y + 46], fill=(222, 234, 248), outline=BLUE, width=2)
    for i, h in enumerate(heads):
        dr.text((cols[i] + 6, y + 12), h, font=_font(15, True), fill=INK)
    y += 46
    rate_mult = Decimal(100 + gst_rate) / Decimal(100)
    sum_taxable = sum_gst = grand = Decimal(0)
    row_h = 76
    for n, it in enumerate(items, 1):
        taxable = (it.total / rate_mult).quantize(Decimal("0.01"), ROUND_HALF_UP)
        gst = it.total - taxable
        sum_taxable, sum_gst, grand = sum_taxable + taxable, sum_gst + gst, grand + it.total
        dr.rectangle([cols[0], y, cols[-1], y + row_h], outline=BLUE, width=1)
        dr.text((cols[0] + 12, y + 12), str(n), font=_font(20), fill=INK)
        dr.text((cols[1] + 6, y + 10), it.name, font=_font(21, True), fill=INK)
        if it.sub:
            dr.text((cols[1] + 6, y + 42), it.sub, font=_font(18), fill=GREY)
        dr.text((cols[2] + 6, y + 12), it.hsn, font=_font(19), fill=INK)
        dr.text((cols[3] + 6, y + 12), f"{it.qty} NOS", font=_font(18), fill=INK)
        for col, val in ((4, inr(taxable)), (5, inr(taxable)), (7, inr(gst)), (8, inr(it.total))):
            _right(dr, cols[col + 1] - 8, y + 12, val, _font(19))
        dr.text((cols[6] + 6, y + 12), f"{gst_rate}.00", font=_font(19), fill=INK)
        y += row_h
    dr.rectangle([cols[0], y, cols[-1], y + 48], fill=(222, 234, 248), outline=BLUE, width=2)
    dr.text((cols[1] + 6, y + 12), "Total", font=_font(21, True), fill=INK)
    dr.text((cols[3] + 6, y + 12), str(sum(i.qty for i in items)), font=_font(20, True), fill=INK)
    _right(dr, cols[6] - 8, y + 12, inr(sum_taxable), _font(19, True))
    _right(dr, cols[8] - 8, y + 12, inr(sum_gst), _font(19, True))
    _right(dr, cols[9] - 8, y + 12, inr(grand), _font(19, True))
    y += 70

    left_top = y
    if words_label:
        dr.rectangle([36, y, 600, y + 150], outline=BLUE, width=2)
        dr.text((318, y + 12), words_label, font=_font(21, True), fill=INK, anchor="ma")
        text = f"{words(int(grand)).upper()} RUPEES ONLY" if words_label == "Total in words" else f"Rupees {words(int(grand))} Only"
        for j, chunk in enumerate(_wrap(text, 44)):
            dr.text((52, y + 54 + j * 28), chunk, font=_font(19), fill=INK)
    dr.text((52, y + 170), "Bank Details", font=_font(21, True), fill=INK)
    for j, (k, v) in enumerate((("Name", bank[0]), ("Branch", bank[1]), ("Acc. Number", bank[2]))):
        dr.text((52, y + 206 + j * 28), k, font=_font(19), fill=INK)
        dr.text((220, y + 206 + j * 28), v, font=_font(19), fill=INK)

    ry = left_top
    rows = [("Taxable Amount", inr(sum_taxable)), (f"Add : IGST", inr(sum_gst)), ("Total Tax", inr(sum_gst))]
    if subtotal_row:
        rows.insert(0, ("Sub Total", inr(sum_taxable)))
    for k, v in rows:
        dr.rectangle([620, ry, W - 36, ry + 34], outline=BLUE, width=1)
        dr.text((630, ry + 6), k, font=_font(19), fill=INK)
        _right(dr, W - 46, ry + 6, v, _font(19))
        ry += 34
    dr.rectangle([620, ry, W - 36, ry + 42], fill=(222, 234, 248), outline=BLUE, width=2)
    dr.text((630, ry + 8), "Total Amount After Tax", font=_font(20, True), fill=INK)
    _right(dr, W - 46, ry + 8, f"Rs. {inr(grand)}", _font(21, True))
    dr.text((W - 46, ry + 70), "(E & O.E.)", font=_font(17), fill=INK, anchor="ra")
    dr.text((W - 46, H - 70), "Authorised Signatory", font=_font(17, True), fill=INK, anchor="ra")
    dr.text((46, H - 70), "Terms: goods once sold will not be taken back.", font=_font(17), fill=GREY)
    img.save(path)
    return grand


def _wrap(text: str, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur]


def make_service_receipt(path: Path, *, centre: str, address: str, job_no: str, repair_date: str, model: str,
                         ident_label: str, ident: str, fault: str, lines: list[tuple[str, Decimal]]) -> Decimal:
    """Service-centre receipt with plain labelled fields followed by a parts/labour table."""
    W, H = 1100, 900 + 56 * len(lines)
    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)
    _banner(dr, W)
    dr.text((46, 80), centre, font=_font(42, True), fill=BLUE)
    dr.text((46, 134), address, font=_font(21), fill=INK)
    dr.line((36, 176, W - 36, 176), fill=INK, width=2)
    dr.text((46, 196), "SERVICE INVOICE / JOB CARD", font=_font(32, True), fill=INK)
    y = 262
    for k, v in (("Job No", job_no), ("Repair Date", repair_date), ("Product Model", model), (ident_label, ident), ("Description", fault)):
        dr.text((46, y), f"{k}: {v}", font=_font(27), fill=INK)
        y += 46
    y += 14
    dr.rectangle([36, y, W - 36, y + 44], fill=(222, 234, 248), outline=BLUE, width=2)
    dr.text((50, y + 10), "Parts / Labour", font=_font(20, True), fill=INK)
    _right(dr, W - 50, y + 10, "Amount (INR)", _font(20, True))
    y += 44
    total = Decimal(0)
    for desc, amt in lines:
        total += amt
        dr.rectangle([36, y, W - 36, y + 52], outline=BLUE, width=1)
        dr.text((50, y + 13), desc, font=_font(21), fill=INK)
        _right(dr, W - 50, y + 13, inr(amt), _font(21))
        y += 52
    y += 26
    dr.text((46, y), f"Total Amount: INR {inr(total)}", font=_font(32, True), fill=INK)
    dr.text((46, y + 56), f"Amount in words: Rupees {words(int(total))} Only", font=_font(21), fill=INK)
    dr.text((46, H - 70), "Warranty on repair: 90 days. Customer signature: ____________", font=_font(18), fill=GREY)
    img.save(path)
    return total


def make_marketplace_invoice(path: Path) -> None:
    """Marketplace-style invoice: two columns, line-item table, Rs symbols, dd.mm.yyyy, amount in words."""
    img = Image.new("RGB", (900, 700), "white")
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, 900, 50], fill=RED)
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
    dr.text((560, 650), "Authorised Signatory", fill="black", font=f)
    img.save(path)


def make_complex_invoice(path: Path) -> None:  # kept for the existing OCR test
    make_marketplace_invoice(path)


# ------------------------------------------------------------------ the demo set
D = Decimal


def build_all(out: Path) -> None:
    def retail(name, **kw):
        make_retail_invoice(out / name, **kw)

    # 001 laptop warranty, clean
    retail("cp001_invoice.png", shop="Digital Hub Electronics", tagline="Laptops, phones and accessories. Easy EMI available",
           address=("Shop 14, Tech Plaza, MG Road", "Bengaluru, Karnataka - 560001"), phone="080 1234 5678", gstin="29FAKE1001A1Z5",
           inv_no="DH/2026/0412", date_label="Invoice Date", date_text="01-Jun-2026", customer="Aarav Demo", place="Karnataka (29)",
           items=[Item("Northstar N14 Laptop 16GB/512GB", D("65000.00"), "Serial No: NS-N14-000123", hsn="8471")])
    # 003 laptop warranty, accidental damage claim
    retail("cp003_invoice.png", shop="Metro Computers", tagline="Authorised retailer. Genuine products only",
           address=("12, Brigade Road", "Bengaluru, Karnataka - 560025"), phone="080 2222 3344", gstin="29FAKE1003C1Z9",
           inv_no="MC/26/0387", date_label="Invoice Date", date_text="15-Mar-2026", customer="Meera Sample", place="Karnataka (29)",
           items=[Item("Northstar N14 Laptop 16GB/512GB", D("62000.00"), "Serial No: NS-N14-000789", hsn="8471")])
    # 004 phone insurance + repair receipt (date conflict)
    retail("cp004_invoice.png", shop="Shree Mobile Point", tagline="Get all your desired smart phones on huge discounts and easy EMI",
           address=("G/45, Vasant Lok Complex", "Pune, Maharashtra - 411001"), phone="020 4455 6677", gstin="27FAKE1004D1Z3",
           inv_no="47", date_label="Invoice Date", date_text="01-Jul-2026", customer="Rohan Demo", place="Maharashtra (27)",
           items=[Item("Aurora A5 5G (8GB/128GB)", D("24000.00"), "IMEI 356938035643809"),
                  Item("20W USB-C Power Adapter", D("1500.00"), hsn="8504")])
    make_service_receipt(out / "cp004_repair_receipt.png", centre="Aurora Care Service Centre", address="Shop 3, Service Lane, Pune - 411002",
                         job_no="JC-26-1187", repair_date="2026-09-29", model="Aurora A5", ident_label="IMEI", ident="356938035643809",
                         fault="Replaced cracked display", lines=[("Display assembly (OEM)", D("8200.00")), ("Labour and testing", D("1600.00"))])
    # 005 phone insurance, clean (approved by a reviewer in the seed)
    retail("cp005_invoice.png", shop="Zenith Telecom World", tagline="All brands, one roof. Exchange offers daily",
           address=("221, Linking Road", "Mumbai, Maharashtra - 400050"), phone="022 6677 8899", gstin="27FAKE1005E1Z1",
           inv_no="ZT-8841", date_label="Invoice Date", date_text="18-May-2026", customer="Isha Sample", place="Maharashtra (27)",
           items=[Item("Zenith Z9 Pro (12GB/256GB)", D("32999.00"), "IMEI 490154203237518")])
    # 006 phone warranty, IMEI differs (invoice shows ...418, claim says ...481)
    retail("cp006_invoice.png", shop="Lumen Mobiles", tagline="Smartphones | Tablets | Accessories",
           address=("7, Anna Salai", "Chennai, Tamil Nadu - 600002"), phone="044 3344 5566", gstin="33FAKE1006F1Z7",
           inv_no="LM/0099", date_label="Invoice Date", date_text="20-Jan-2026", customer="Karthik Demo", place="Tamil Nadu (33)",
           items=[Item("Lumen L3 (6GB/128GB)", D("18499.00"), "IMEI 352099001761418")], subtotal_row=True)
    # 007 laptop warranty, outside the 12 month window
    retail("cp007_invoice.png", shop="Capital Laptops", tagline="Specialists in business laptops",
           address=("Unit 5, Nehru Place", "New Delhi - 110019"), phone="011 5566 7788", gstin="07FAKE1007G1Z2",
           inv_no="CL-5531", date_label="Date", date_text="10-Feb-2025", customer="Nikhil Sample", place="Delhi (07)",
           items=[Item("Northstar N15 Laptop 16GB/1TB", D("84000.00"), "Serial No: NS-N15-000842", hsn="8471")])
    # 008 laptop insurance over the cap
    retail("cp008_invoice.png", shop="Digital Hub Electronics", tagline="Laptops, phones and accessories. Easy EMI available",
           address=("Shop 14, Tech Plaza, MG Road", "Bengaluru, Karnataka - 560001"), phone="080 1234 5678", gstin="29FAKE1001A1Z5",
           inv_no="DH/2026/0129", date_label="Invoice Date", date_text="05-Feb-2026", customer="Divya Demo", place="Karnataka (29)",
           items=[Item("Northstar N14 Laptop 32GB/1TB", D("78000.00"), "Serial No: NS-N14-000555", hsn="8471")])
    # 009 phone insurance, purchase date written 06/04/2026 (ambiguous: 6 April or 4 June)
    retail("cp009_invoice.png", shop="Vega Mobile Hub", tagline="Best prices on the latest smartphones",
           address=("Shop 9, Station Road", "Trichy, Tamil Nadu - 620001"), phone="0431 223344", gstin="33FAKE1009H1Z4",
           inv_no="122026/1266", date_label="Date", date_text="06/04/2026", customer="Mowni Sample", place="Tamil Nadu (33)",
           items=[Item("Vega V1 (8GB/128GB)", D("21999.00"), "IMEI 861234050987654")], words_label="Amount in Words", subtotal_row=True)
    # 010 phone insurance, repair already done but no receipt yet
    retail("cp010_invoice.png", shop="Nimbus Phones", tagline="Authorised partner. Service and support",
           address=("14, Park Street", "Kolkata, West Bengal - 700016"), phone="033 7788 9900", gstin="19FAKE1010J1Z6",
           inv_no="NP-3120", date_label="Invoice Date", date_text="10-Jun-2026", customer="Sneha Demo", place="West Bengal (19)",
           items=[Item("Nimbus N2 (8GB/256GB)", D("27999.00"), "IMEI 867530123456780")])
    make_marketplace_invoice(out / "complex_marketplace_invoice.png")
    (out / "cp002_statement.txt").write_text(
        "FAKE - SYNTHETIC DEMO DOCUMENT\nCustomer Statement\nIncident Date: 2026-10-02\n"
        "Description: Laptop slipped from desk and the screen cracked.\n", encoding="utf-8")


def ensure_fixtures() -> Path:
    FIXTURE_DIR.mkdir(exist_ok=True)
    marker = FIXTURE_DIR / ".version"
    if not marker.exists() or marker.read_text().strip() != FIXTURE_VERSION or not (FIXTURE_DIR / "cp010_invoice.png").exists():
        build_all(FIXTURE_DIR)
        marker.write_text(FIXTURE_VERSION)
    return FIXTURE_DIR


if __name__ == "__main__":
    print(ensure_fixtures())
