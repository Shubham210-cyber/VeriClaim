"""Deterministic label-based fact parsers + normalizers (docs/DECISIONS.md)."""
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.documents.extract import ExtractionResult
from app.enums import EvidenceType, FieldName

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

LABELS: dict[FieldName, list[str]] = {
    FieldName.PRODUCT_MODEL: ["product model", "device model", "model"],
    FieldName.DEVICE_IDENTIFIER: ["serial number", "serial no", "serial", "imei", "device id"],
    FieldName.PURCHASE_DATE: ["purchase date", "date of purchase", "invoice date"],
    FieldName.INCIDENT_DATE: ["incident date", "date of incident", "date of loss"],
    FieldName.REPAIR_DATE: ["repair date", "service date", "date of repair"],
    FieldName.EVENT_DESCRIPTION: ["damage description", "failure description", "description", "statement", "issue"],
}
AMOUNT_LABELS = ["repair amount", "total amount", "amount paid", "amount", "total"]


@dataclass
class ParsedFact:
    field_name: FieldName
    raw_value: str
    normalized_value: str | None
    snippet: str
    page: int


def parse_date(raw: str) -> str | None:
    """ISO date or None. Ambiguous numeric DD/MM vs MM/DD returns None (-> INDETERMINATE)."""
    s = raw.strip().strip(".")
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{1,2})[ \-/]([A-Za-z]{3,9})[ \-/,]+(\d{4})", s)
    if m and m[2][:3].lower() in _MONTHS:
        try:
            return date(int(m[3]), _MONTHS[m[2][:3].lower()], int(m[1])).isoformat()
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", s)
    if m:
        a, b, y = int(m[1]), int(m[2]), int(m[3])
        if a <= 12 and b <= 12 and a != b:
            return None  # ambiguous
        day, mon = (a, b) if a > 12 else (b, a) if b > 12 else (a, b)
        try:
            return date(y, mon, day).isoformat()
        except ValueError:
            return None
    return None


def normalize_identifier(raw: str) -> str:
    return re.sub(r"\s+", "", raw).upper()


def normalize_model(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip().lower()


def parse_amount(raw: str) -> tuple[str | None, str | None]:
    """Return (decimal_string, currency_code)."""
    cur = None
    if re.search(r"\bINR\b|₹|\bRs\.?", raw, re.I):
        cur = "INR"
    elif re.search(r"\bUSD\b|\$", raw, re.I):
        cur = "USD"
    elif re.search(r"\bEUR\b|€", raw, re.I):
        cur = "EUR"
    m = re.search(r"\d[\d,]*(?:\.\d{1,2})?", raw)
    if not m:
        return None, cur
    try:
        return str(Decimal(m.group(0).replace(",", "")).quantize(Decimal("0.01"))), cur
    except InvalidOperation:
        return None, cur


def _find(lines: list[tuple[int, str]], labels: list[str]) -> tuple[str, str, int] | None:
    for label in labels:
        rx = re.compile(rf"^\W*{re.escape(label)}\s*[:=\-]\s*(.+?)\s*$", re.I)
        for page, line in lines:
            m = rx.match(line)
            if m:
                return m.group(1), line.strip(), page
    return None


def parse_document(result: ExtractionResult, evidence_type: EvidenceType) -> list[ParsedFact]:
    lines = [(p.page, ln) for p in result.pages for ln in p.text.splitlines() if ln.strip()]
    out: list[ParsedFact] = []
    for field, labels in LABELS.items():
        hit = _find(lines, labels)
        if not hit:
            continue
        raw, snippet, page = hit
        if field in (FieldName.PURCHASE_DATE, FieldName.INCIDENT_DATE, FieldName.REPAIR_DATE):
            norm = parse_date(raw)
        elif field == FieldName.DEVICE_IDENTIFIER:
            norm = normalize_identifier(raw)
        elif field == FieldName.PRODUCT_MODEL:
            norm = normalize_model(raw)
        else:
            norm = raw.strip()
        out.append(ParsedFact(field, raw, norm, snippet, page))
    amount_field = {EvidenceType.PURCHASE_INVOICE: FieldName.PURCHASE_AMOUNT,
                    EvidenceType.REPAIR_RECEIPT: FieldName.REPAIR_AMOUNT}.get(evidence_type)
    if amount_field:
        hit = _find(lines, AMOUNT_LABELS)
        if hit:
            raw, snippet, page = hit
            amt, cur = parse_amount(raw)
            out.append(ParsedFact(amount_field, raw, amt, snippet, page))
            if cur:
                out.append(ParsedFact(FieldName.CURRENCY, cur, cur, snippet, page))
    return out
