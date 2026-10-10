"""Text extraction: TXT, digital PDF (pypdf), images (Tesseract behind OcrEngine)."""
import io
import logging
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.enums import ExtractionMethod

log = logging.getLogger(__name__)
MAX_TEXT = 20000
OCR_MAX_CONF = 0.90        # OCR confidence is a routing heuristic; never present it as certainty
OCR_TARGET_WIDTH = 2400    # small scans/screenshots are upscaled to roughly this width
OCR_PSM_MODES = (6, 4)     # 6 = uniform block (tables), 4 = columns of variable size (two-column invoices)


@dataclass
class PageText:
    page: int
    text: str
    line_conf: dict[str, float] = field(default_factory=dict)  # line text -> robust confidence (0..1)


@dataclass
class ExtractionResult:
    pages: list[PageText]
    method: ExtractionMethod
    confidence: float | None  # document-level; None = not available
    error_code: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(p.text for p in self.pages)


def _fail(code: str, method: ExtractionMethod = ExtractionMethod.REGEX) -> ExtractionResult:
    return ExtractionResult([], method, None, code)


def preprocess(img):
    """Grayscale, upscale small images, stretch contrast and sharpen: big accuracy win on screenshots."""
    from PIL import Image, ImageFilter, ImageOps
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, "white")  # flatten transparency onto white
        bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
        img = bg
    g = ImageOps.grayscale(img)
    w, _ = g.size
    if w < OCR_TARGET_WIDTH:
        scale = min(4, math.ceil(OCR_TARGET_WIDTH / w))
        g = g.resize((g.width * scale, g.height * scale), Image.Resampling.LANCZOS)
    g = ImageOps.autocontrast(g, cutoff=1)
    return g.filter(ImageFilter.SHARPEN)


class TesseractOcr:
    """OcrEngine adapter. Swap for another engine by returning the same shape."""

    def _run_mode(self, pytesseract, img, psm: int) -> tuple[list[tuple[str, float]], float]:
        d = pytesseract.image_to_data(img, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
        lines: dict[tuple, list[tuple[str, float]]] = {}
        confs: list[float] = []
        for i, word in enumerate(d["text"]):
            if not word.strip():
                continue
            c = float(d["conf"][i])
            if c >= 0:
                confs.append(c)
            lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append((word, max(c, 0.0)))
        out = [(" ".join(w for w, _ in ws), statistics.median(c for _, c in ws) / 100.0) for ws in lines.values()]
        return out, (sum(confs) / len(confs) / 100.0 if confs else 0.0)

    def run(self, data: bytes) -> ExtractionResult:
        try:
            import pytesseract
            from PIL import Image, UnidentifiedImageError
        except ImportError:
            return _fail("OCR_UNAVAILABLE", ExtractionMethod.OCR)
        if not Path(settings.tesseract_cmd).exists():
            return _fail("OCR_UNAVAILABLE", ExtractionMethod.OCR)
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except (UnidentifiedImageError, OSError, ValueError):
            return _fail("CORRUPT_FILE", ExtractionMethod.OCR)
        try:
            prepped = preprocess(img)
            variants = [self._run_mode(pytesseract, prepped, psm) for psm in OCR_PSM_MODES]
        except Exception:  # tesseract runtime failure: technical, not a claim outcome
            log.exception("OCR failed")
            return _fail("OCR_FAILED", ExtractionMethod.OCR)
        # Merge the layout variants: the parser takes the first label hit, so keep the better variant first.
        variants.sort(key=lambda v: v[1], reverse=True)
        seen: set[str] = set()
        text_lines: list[str] = []
        line_conf: dict[str, float] = {}
        for lines, _ in variants:
            for text, conf in lines:
                line_conf[text] = max(line_conf.get(text, 0.0), min(OCR_MAX_CONF, conf))
                if text not in seen:
                    seen.add(text)
                    text_lines.append(text)
        text = "\n".join(text_lines)
        if not text.strip():
            return _fail("NO_TEXT_FOUND", ExtractionMethod.OCR)
        doc_conf = min(OCR_MAX_CONF, variants[0][1])
        return ExtractionResult([PageText(1, text[:MAX_TEXT], line_conf)], ExtractionMethod.OCR, round(doc_conf, 3))


ocr_engine = TesseractOcr()


def extract(ext: str, data: bytes) -> ExtractionResult:
    if ext == ".txt":
        return ExtractionResult([PageText(1, data.decode("utf-8")[:MAX_TEXT])], ExtractionMethod.REGEX, 0.95)
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            pages = [PageText(i + 1, (p.extract_text() or "")[:MAX_TEXT]) for i, p in enumerate(reader.pages)]
        except Exception:
            return _fail("CORRUPT_FILE")
        if not any(p.text.strip() for p in pages):
            # Scanned PDF: rendering pages for OCR is out of MVP scope. Not evidence of absence.
            return _fail("NO_TEXT_LAYER")
        return ExtractionResult(pages, ExtractionMethod.REGEX, 0.95)
    if ext in (".png", ".jpg", ".jpeg"):
        return ocr_engine.run(data)
    return _fail("UNSUPPORTED")
