from __future__ import annotations

import io
import logging
import subprocess
import time
from dataclasses import dataclass, field

import pypdfium2 as pdfium

from app.core.config import settings
from app.core.observability import observe_source_enrichment

logger = logging.getLogger("research-worker.ocr")


@dataclass(slots=True)
class OCRPage:
    page: int
    text: str


@dataclass(slots=True)
class OCRResult:
    pages: list[OCRPage] = field(default_factory=list)
    total_pages: int = 0
    pages_attempted: int = 0
    limitation_code: str | None = None
    limitation_message: str | None = None

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages).strip()


def _failure(code: str, message: str, *, total_pages: int = 0, attempted: int = 0) -> OCRResult:
    return OCRResult(
        total_pages=total_pages,
        pages_attempted=attempted,
        limitation_code=code,
        limitation_message=message,
    )


def _finish(result: OCRResult, started: float, *, outcome: str | None = None) -> OCRResult:
    outcome = outcome or ("success" if result.text else "error")
    duration_seconds = time.monotonic() - started
    observe_source_enrichment(
        operation="pdf-ocr",
        outcome=outcome,
        error_code=result.limitation_code,
        duration_seconds=duration_seconds,
    )
    logger.info(
        "OCR enrichment completed",
        extra={
            "action": "source.enrichment.completed",
            "operation": "pdf-ocr",
            "outcome": outcome,
            "error_code": result.limitation_code,
            "duration_ms": round(duration_seconds * 1000, 2),
            "page_count": result.pages_attempted,
            "output_chars": len(result.text),
        },
    )
    return result


def ocr_pdf(content: bytes) -> OCRResult:
    """Run bounded local OCR without persisting page images or command output."""

    started = time.monotonic()
    if not settings.ocr_enabled:
        return _finish(
            _failure(
                # Naming the disabled feature is what makes this recoverable: the operator
                # can enable OCR, or the researcher can supply a text-based PDF.
                "PDF_SCANNED_OCR_DISABLED",
                "The PDF is a scan with no text layer, and OCR is disabled on this server.",
            ),
            started,
            outcome="disabled",
        )

    try:
        document = pdfium.PdfDocument(content)
    except Exception:
        return _finish(
            _failure("OCR_FAILED", "The scanned PDF could not be prepared for OCR."),
            started,
        )

    total_pages = len(document)
    page_budget = min(total_pages, max(1, min(settings.ocr_max_pages, 100)))
    pages: list[OCRPage] = []
    try:
        for index in range(page_budget):
            timeout_seconds = max(1, min(settings.ocr_timeout_seconds, 120))
            remaining = timeout_seconds - (time.monotonic() - started)
            if remaining <= 0:
                return _finish(
                    _failure(
                        "OCR_FAILED",
                        "OCR exceeded the configured document timeout.",
                        total_pages=total_pages,
                        attempted=index,
                    ),
                    started,
                    outcome="timeout",
                )
            page = document[index]
            width, height = page.get_size()
            desired_scale = min(max(72, settings.ocr_dpi), 400) / 72
            max_pixels = max(1_000_000, min(settings.ocr_max_pixels, 50_000_000))
            pixel_scale = (max_pixels / max(1, width * height)) ** 0.5
            bitmap = page.render(scale=min(desired_scale, pixel_scale))
            image = bitmap.to_pil()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            try:
                completed = subprocess.run(
                    [
                        settings.ocr_command,
                        "stdin",
                        "stdout",
                        "-l",
                        settings.ocr_languages,
                        "--psm",
                        "3",
                    ],
                    input=buffer.getvalue(),
                    capture_output=True,
                    check=False,
                    timeout=max(0.1, remaining),
                )
            except FileNotFoundError:
                return _finish(
                    _failure(
                        "OCR_UNAVAILABLE",
                        "The configured OCR engine is unavailable.",
                        total_pages=total_pages,
                        attempted=index,
                    ),
                    started,
                    outcome="unavailable",
                )
            except subprocess.TimeoutExpired:
                return _finish(
                    _failure(
                        "OCR_FAILED",
                        "OCR exceeded the configured document timeout.",
                        total_pages=total_pages,
                        attempted=index + 1,
                    ),
                    started,
                    outcome="timeout",
                )
            if completed.returncode != 0:
                return _finish(
                    _failure(
                        "OCR_FAILED",
                        "The OCR engine could not read the scanned PDF.",
                        total_pages=total_pages,
                        attempted=index + 1,
                    ),
                    started,
                )
            page_text = completed.stdout.decode("utf-8", errors="replace").strip()
            if page_text:
                pages.append(OCRPage(page=index + 1, text=page_text))
            output_limit = max(1, min(settings.ocr_max_output_chars, 500_000))
            if len("\n\n".join(page.text for page in pages)) >= output_limit:
                previous_chars = sum(len(item.text) for item in pages[:-1])
                separator_chars = max(0, len(pages) - 1) * 2
                pages[-1].text = pages[-1].text[
                    : max(0, output_limit - previous_chars - separator_chars)
                ]
                result = OCRResult(
                    pages=pages,
                    total_pages=total_pages,
                    pages_attempted=index + 1,
                    limitation_code="OCR_TEXT_LIMIT",
                    limitation_message="OCR đã đạt giới hạn văn bản được cấu hình.",
                )
                return _finish(result, started)
    except Exception:
        return _finish(
            _failure(
                "OCR_FAILED",
                "The scanned PDF could not be rendered for OCR.",
                total_pages=total_pages,
                attempted=len(pages),
            ),
            started,
        )
    finally:
        document.close()

    result = OCRResult(pages=pages, total_pages=total_pages, pages_attempted=page_budget)
    if len(result.text) < max(1, settings.ocr_min_chars):
        result.limitation_code = "OCR_FAILED"
        result.limitation_message = "OCR không khôi phục được đủ văn bản có thể đọc."
    elif total_pages > page_budget:
        result.limitation_code = "OCR_PAGE_LIMIT"
        result.limitation_message = f"OCR processed only the first {page_budget} pages."
    return _finish(result, started)
