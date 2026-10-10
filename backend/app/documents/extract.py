"""Text extraction: TXT, digital PDF (pypdf), images (Tesseract behind OcrEngine)."""
import io
import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.enums import ExtractionMethod

log = logging.getLogger(__name__)
MAX_TEXT = 20000


@dataclass
class PageText:
    page: int
    text: str


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


class TesseractOcr:
    """OcrEngine adapter. Swap for another engine by returning the same shape."""

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
            d = pytesseract.image_to_data(img.convert("RGB"), output_type=pytesseract.Output.DICT)
        except Exception:  # tesseract runtime failure: technical, not a claim outcome
            log.exception("OCR failed")
            return _fail("OCR_FAILED", ExtractionMethod.OCR)
        lines: dict[tuple, list[str]] = {}
        confs: list[float] = []
        for i, word in enumerate(d["text"]):
            if not word.strip():
                continue
            c = float(d["conf"][i])
            if c >= 0:
                confs.append(c)
            lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append(word)
        text = "\n".join(" ".join(ws) for ws in lines.values())
        if not text.strip():
            return _fail("NO_TEXT_FOUND", ExtractionMethod.OCR)
        conf = min(0.90, (sum(confs) / len(confs) / 100.0) if confs else 0.0)
        return ExtractionResult([PageText(1, text[:MAX_TEXT])], ExtractionMethod.OCR, round(conf, 3))


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
