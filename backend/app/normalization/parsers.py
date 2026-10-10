"""Deterministic fact parsers + normalizers (docs/DECISIONS.md).

Works on messy real-world text: labels may sit mid-line (two-column invoices), values are matched by shape
(date / identifier / money) rather than "rest of line", and the product can come from the invoice line-item table.
Optional claim `hints` let us *locate* the claimed model/identifier in the document text; the resulting fact always
quotes text that is really in the document, so nothing is invented.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from app.documents.extract import ExtractionResult
from app.enums import EvidenceType, FieldName

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

DATE_VALUE = (r"(\d{4}-\d{2}-\d{2}|\d{1,2}\s?[./-]\s?\d{1,2}\s?[./-]\s?\d{4}|"
              r"\d{1,2}[ -][A-Za-z]{3,9}[ ,.-]+\d{4})")
DATE_LABELS: dict[FieldName, list[str]] = {
    FieldName.PURCHASE_DATE: ["purchase date", "date of purchase", "invoice date", "order date", "bill date"],
    FieldName.INCIDENT_DATE: ["incident date", "date of incident", "date of loss"],
    FieldName.REPAIR_DATE: ["repair date", "service date", "date of repair", "completed on"],
}
ID_LABELS = ["serial number", "serial no", "serial", "imei 1", "imei", "device id"]
ID_VALUE = r"([A-Za-z0-9][A-Za-z0-9\-/]{5,24})"
MODEL_LABELS = ["product model", "device model", "model name", "model no", "model"]
DESC_LABELS = ["damage description", "failure description", "description", "statement", "issue"]
AMOUNT_LABELS = ["repair amount", "grand total", "total amount", "amount paid", "net payable", "total", "amount"]
MONEY = re.compile(r"\d[\d,]*\.\d{2}")
SUBTOTAL = re.compile(r"sub\s*-?\s*total|taxable|before\s+tax", re.I)
TABLE_GUESS_MAX_CONF = 0.75  # heuristic table-derived values stay below the 0.80 reliability threshold


@dataclass
class ParsedFact:
    field_name: FieldName
    raw_value: str
    normalized_value: str | None
    snippet: str
    page: int
    confidence: float | None = None  # per-fact (line-level) confidence when the extractor provides it


@dataclass
class Hints:
    """Values the claimant stated; used only to locate/verify text in the document."""
    model: str | None = None        # e.g. "Nokia 2" (brand + model)
    model_only: str | None = None   # e.g. "iPhone 15 Pro Max": invoices often omit the brand prefix
    identifier: str | None = None
    extra: dict = field(default_factory=dict)


def parse_date(raw: str) -> str | None:
    """ISO date or None. Ambiguous numeric DD/MM vs MM/DD returns None (-> INDETERMINATE)."""
    s = re.sub(r"\s+", "", raw.strip().strip(".")) if re.search(r"\d\s?[./-]\s?\d", raw) else raw.strip().strip(".")
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{1,2})[ \-/.]([A-Za-z]{3,9})[ \-/.,]+(\d{4})", s)
    if m and m[2][:3].lower() in _MONTHS:
        try:
            return date(int(m[3]), _MONTHS[m[2][:3].lower()], int(m[1])).isoformat()
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", s)
    if m:
        a, b, y = int(m[1]), int(m[2]), int(m[3])
        if a <= 12 and b <= 12 and a != b:
            return None  # ambiguous: 03/04/2026 could be 3 April or 4 March
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


def parse_amount(raw: str, doc_text: str = "") -> tuple[str | None, str | None]:
    """Return (decimal_string, currency_code). Takes the LAST money value on the line (line totals sit rightmost)."""
    cur = None
    if re.search(r"\bINR\b|₹|\bRs\.?|\bIGST\b|\bCGST\b|\bGST\b", raw + " " + doc_text, re.I):
        cur = "INR"
    elif re.search(r"\bUSD\b|\$", raw, re.I):
        cur = "USD"
    elif re.search(r"\bEUR\b|€", raw, re.I):
        cur = "EUR"
    nums = MONEY.findall(raw) or re.findall(r"\d[\d,]*", raw)
    if not nums:
        return None, cur
    try:
        return str(Decimal(nums[-1].replace(",", "")).quantize(Decimal("0.01"))), cur
    except InvalidOperation:
        return None, cur


_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
_SCALES = {"thousand": 1_000, "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "crore": 10_000_000, "crores": 10_000_000}
_FILLER = {"and", "only", "rupees", "rupee", "rs", "inr", "dollars", "dollar", "usd", "euro", "euros"}


def words_to_number(text: str) -> Decimal | None:
    """'Six Thousand One Hundred And Eighty only' -> 6180. Returns None on any unrecognised word (never guesses)."""
    main, _, paise_part = text.lower().partition("paise")
    total, current, seen = 0, 0, False

    def run(words: list[str]) -> int | None:
        nonlocal seen
        tot = cur = 0
        for w in words:
            if w in _FILLER:
                continue
            seen = True
            if w in _UNITS:
                cur += _UNITS[w]
            elif w in _TENS:
                cur += _TENS[w]
            elif w == "hundred":
                cur = max(cur, 1) * 100
            elif w in _SCALES:
                tot += max(cur, 1) * _SCALES[w]
                cur = 0
            else:
                return None
        return tot + cur

    toks = re.findall(r"[a-z]+", main)
    if not toks:
        return None
    if paise_part is not None and "paise" in text.lower():
        before, _, after = main.partition(" and ")
        rupees, paise = run(re.findall(r"[a-z]+", before)), run(re.findall(r"[a-z]+", after))
        if rupees is None or paise is None:
            return None
        return Decimal(rupees) + Decimal(paise) / 100
    val = run(toks)
    return Decimal(val) if val is not None and seen else None


Line = tuple[int, str, float | None]  # page, text, confidence


def _label_rx(label: str) -> str:
    return r"(?<![A-Za-z])" + r"\s+".join(re.escape(w) for w in label.split())


def _find_by_shape(lines: list[Line], labels: list[str], value_rx: str, flags=re.I):
    """Label anywhere on the line, immediately followed (<=3 junk chars) by a value of the right shape."""
    for label in labels:
        rx = re.compile(_label_rx(label) + r"\W{0,3}" + value_rx, flags)
        for page, line, conf in lines:
            m = rx.search(line)
            if m:
                return m.group(m.lastindex), line.strip(), page, conf
    return None


def _find_rest_of_line(lines: list[Line], labels: list[str]):
    for label in labels:
        rx = re.compile(r"^\W*" + _label_rx(label)[len("(?<![A-Za-z])"):] + r"\s*[:=\-]\s*(.+?)\s*$", re.I)
        for page, line, conf in lines:
            m = rx.match(line)
            if m:
                return m.group(1), line.strip(), page, conf
    return None


def _table_product(lines: list[Line]):
    """Product from an invoice line-item table: first row under the 'Description' header."""
    for i, (_, line, _) in enumerate(lines):
        window = line + " " + (lines[i + 1][1] if i + 1 < len(lines) else "")
        if re.search(r"\b(description|product)\b", line, re.I) and re.search(r"\b(qty|quantity|price|amount|rate|tax|hsn)\b", window, re.I):
            for page, nxt, conf in lines[i + 1:i + 5]:
                s = re.sub(r"^\W*\d{1,2}\s+", "", nxt).strip()
                s = re.split(r"\||\bHSN\b|[₹$€]|\bRs\b", s)[0]
                s = MONEY.split(s)[0].strip(" -:|")
                if len(s) >= 3 and len(re.findall(r"[A-Za-z]", s)) >= 3:
                    return s, nxt.strip(), page, conf
    return None


def _locate(lines: list[Line], pattern: str, squash: bool = False):
    rx = re.compile(pattern, re.I)
    for page, line, conf in lines:
        m = rx.search(re.sub(r"\s", "", line) if squash else line)
        if m:
            return m.group(0), line.strip(), page, conf
    return None


def _model_pattern(model: str) -> str:
    toks = re.findall(r"[A-Za-z]+|\d+(?:\.\d+)?", model)
    # Standalone token only: never match inside a serial/IMEI/SKU such as "NS-N14-000123".
    return (r"(?<![A-Za-z0-9\-_/])" + r"[\s\-]*".join(re.escape(t) for t in toks) + r"(?![A-Za-z0-9.\-_/])") if toks else r"$^"


def parse_document(result: ExtractionResult, evidence_type: EvidenceType, hints: Hints | None = None) -> list[ParsedFact]:
    lines: list[Line] = [(p.page, ln.strip(), p.line_conf.get(ln)) for p in result.pages for ln in p.text.splitlines() if ln.strip()]
    doc_text = result.text
    out: list[ParsedFact] = []

    def add(field_name, raw, norm, snippet, page, conf):
        out.append(ParsedFact(field_name, raw.strip(), norm, snippet, page, conf))

    for field_name, labels in DATE_LABELS.items():
        hit = _find_by_shape(lines, labels, DATE_VALUE)
        if not hit and field_name == FieldName.PURCHASE_DATE and evidence_type == EvidenceType.PURCHASE_INVOICE:
            # Many shop invoices just say "Date : 06/04/2026". Only trusted on an invoice, never on a claim form.
            hit = _find_by_shape(lines, ["date"], DATE_VALUE)
        if hit:
            raw, snip, page, conf = hit
            add(field_name, raw, parse_date(raw), snip, page, conf)

    hit = _find_by_shape(lines, ID_LABELS, ID_VALUE)
    if hit and re.search(r"\d", hit[0]):
        raw, snip, page, conf = hit
        add(FieldName.DEVICE_IDENTIFIER, raw, normalize_identifier(raw), snip, page, conf)
    elif hints and hints.identifier:
        # Claimant stated an identifier: confirm it literally appears in the document (spaces/hyphens tolerated).
        want = re.sub(r"[\s\-]", "", hints.identifier).upper()
        for page, line, conf in lines:
            squashed = re.sub(r"[\s\-]", "", line).upper()
            if want and want in squashed:
                add(FieldName.DEVICE_IDENTIFIER, hints.identifier, normalize_identifier(hints.identifier), line, page, conf)
                break

    # Model: an explicit label wins; then the claimed model literally found in the text (verification);
    # last resort is the line-item table, whose OCR is noisy, so it is capped below the confidence threshold
    # (it will ask for verification rather than accuse on a possible misread such as "A5" -> "Ad").
    hit = _find_rest_of_line(lines, MODEL_LABELS)
    loc = None
    if not hit and hints:
        for cand in (hints.model, hints.model_only):
            # a bare model like "2" is too weak to search for; require letters and some length
            if cand and len(cand) >= 3 and re.search(r"[A-Za-z]", cand):
                loc = _locate(lines, _model_pattern(cand))
                if loc:
                    break
    if hit or loc:
        raw, snip, page, conf = hit or loc
        add(FieldName.PRODUCT_MODEL, raw, normalize_model(raw), snip, page, conf)
    else:
        tbl = _table_product(lines)
        if tbl:
            raw, snip, page, conf = tbl
            add(FieldName.PRODUCT_MODEL, raw, normalize_model(raw), snip, page, min(conf if conf is not None else 0.75, TABLE_GUESS_MAX_CONF))

    hit = _find_rest_of_line(lines, DESC_LABELS)
    if hit:
        raw, snip, page, conf = hit
        add(FieldName.EVENT_DESCRIPTION, raw, raw.strip(), snip, page, conf)

    amount_field = {EvidenceType.PURCHASE_INVOICE: FieldName.PURCHASE_AMOUNT,
                    EvidenceType.REPAIR_RECEIPT: FieldName.REPAIR_AMOUNT}.get(evidence_type)
    if amount_field:
        words = _amount_in_words(lines)  # (value, text, page, conf) or None
        labelled = None
        for label in AMOUNT_LABELS:
            rx = re.compile(_label_rx(label) + r"\b", re.I)
            # "Sub Total" / "Taxable amount" lines are not the payable total even though they contain "total"
            labelled = next(((p, ln, c) for p, ln, c in lines
                             if rx.search(ln) and MONEY.search(ln) and not SUBTOTAL.search(ln)), None)
            if labelled:
                break
        if labelled:
            page, ln, conf = labelled
            amt, cur = parse_amount(ln, doc_text)
            m0 = re.search(_label_rx(label) + r"\b", ln, re.I)
            ln = ln[m0.start():] if m0 else ln  # drop unrelated text merged from a neighbouring column
            if words:
                # Cross-check numeric total against the spelled-out total: agreement raises trust (OCR garbles
                # currency symbols, so numeric lines score low); disagreement forces verification.
                agree = amt is not None and Decimal(amt) == words[0]
                known = [c for c in (conf, words[3]) if c is not None]
                conf = (max(known) if known else None) if agree else min(conf if conf is not None else 0.5, 0.5)
            add(amount_field, ln, amt, ln, page, conf)
            if cur:
                add(FieldName.CURRENCY, cur, cur, ln, page, conf)
        elif words:
            # No readable money line: use the spelled-out total (skipped entirely if any word is unrecognised).
            value, text, page, conf = words
            cur = "INR" if re.search(r"\bGST\b|\bIGST\b|rupee|\bINR\b", doc_text, re.I) else None
            snippet = f"Amount in Words: {text}"
            add(amount_field, text, str(value.quantize(Decimal("0.01"))), snippet, page, conf)
            if cur:
                add(FieldName.CURRENCY, cur, cur, snippet, page, conf)
    return out


def _amount_in_words(lines: list[Line]):
    """Spelled-out total: after an 'amount/total in words' label, or a standalone line ending in 'only'."""
    for i, (page, ln, conf) in enumerate(lines):
        m = re.search(r"(?:total\s+|amount\s+)?in\s+words\W*(.*)$", ln, re.I)
        if m:
            if m.group(1).strip():
                cand, cpage, cconf = m.group(1).strip(), page, conf
            elif i + 1 < len(lines):
                cpage, cand, cconf = lines[i + 1]
            else:
                continue
            value = words_to_number(cand) if cand else None
            if value is not None and value > 0:
                return value, cand, cpage, cconf
    for page, ln, conf in lines:
        m = re.match(r"^\W*(?:rupees\s+|amount\s*:\s*)?([A-Za-z ,\-]+?)\s+only\.?\W*$", ln.strip(), re.I)
        if m:
            value = words_to_number(m.group(1))
            if value is not None and value > 0:
                return value, ln.strip(), page, conf
    return None
