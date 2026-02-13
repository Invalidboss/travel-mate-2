"""Receipt ingestion and parsing pipeline.

This module provides a deployment-friendly receipt pipeline that:
- accepts image/PDF uploads
- runs OCR via a pluggable provider interface
- extracts normalized financial fields
- classifies receipts into expense categories
- flags low-confidence items for manual review
- stores raw and parsed outputs for auditability
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple


# -----------------------------
# Data contracts
# -----------------------------


@dataclass(frozen=True)
class UploadedDocument:
    """Input payload for receipt processing."""

    filename: str
    content_type: str
    content: bytes

    def validate(self) -> None:
        supported = {
            "application/pdf",
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/webp",
            "image/tiff",
            "image/heic",
        }
        if self.content_type.lower() not in supported:
            raise ValueError(
                f"Unsupported content type '{self.content_type}'. "
                f"Supported values: {sorted(supported)}"
            )


@dataclass
class ParsedReceipt:
    date: Optional[str] = None
    merchant: Optional[str] = None
    total_amount: Optional[float] = None
    vat: Optional[float] = None
    currency: Optional[str] = None
    payment_type: Optional[str] = None


@dataclass
class ClassificationResult:
    suggested_category: str
    confidence: float
    matched_keywords: List[str] = field(default_factory=list)


@dataclass
class ReceiptAuditRecord:
    """Audit payload that can be persisted in DB/document store."""

    filename: str
    content_type: str
    raw_ocr_text: str
    parsed_output: ParsedReceipt
    suggested_category: str
    confidence_score: float
    requires_manual_review: bool

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # normalize naming for API payload conventions
        result["parsed_output"] = asdict(self.parsed_output)
        return result


# -----------------------------
# OCR provider abstraction
# -----------------------------


class OCRProvider(Protocol):
    """Common OCR interface for Tesseract/Azure/AWS implementations."""

    def extract_text(self, document: UploadedDocument) -> str:
        ...


class TesseractOCRProvider:
    """Placeholder provider for local Tesseract integration."""

    def extract_text(self, document: UploadedDocument) -> str:
        # Integrate pytesseract + image/PDF conversion in deployment.
        raise NotImplementedError("Tesseract OCR integration is not configured")


class AzureReadOCRProvider:
    """Placeholder provider for Azure Document Intelligence/Read API."""

    def extract_text(self, document: UploadedDocument) -> str:
        # Integrate Azure SDK calls in deployment.
        raise NotImplementedError("Azure OCR integration is not configured")


class TextractOCRProvider:
    """Placeholder provider for AWS Textract."""

    def extract_text(self, document: UploadedDocument) -> str:
        # Integrate boto3 Textract calls in deployment.
        raise NotImplementedError("AWS Textract integration is not configured")


class MockOCRProvider:
    """Provider useful for tests and local development."""

    def __init__(self, text: str):
        self._text = text

    def extract_text(self, document: UploadedDocument) -> str:
        _ = document
        return self._text


# -----------------------------
# Parsing helpers
# -----------------------------


_CURRENCY_SYMBOL_TO_CODE = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}

_CURRENCY_CODE_RE = re.compile(r"\b(USD|EUR|GBP|JPY|CAD|AUD|CHF|INR|AED|SGD)\b", re.IGNORECASE)
_DATE_PATTERNS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%d.%m.%Y",
]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_decimal(raw: str) -> Optional[Decimal]:
    cleaned = raw.replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _extract_total(text: str) -> Tuple[Optional[float], float]:
    patterns = [
        r"(?i)\b(total|amount due|grand total|paid)\b[^\d]{0,10}([\d]+(?:[\.,]\d{2})?)",
        r"(?i)\b([\d]+(?:[\.,]\d{2})?)\s*(usd|eur|gbp|jpy|cad|aud|chf|inr|aed|sgd|[$€£¥])\b",
    ]
    for idx, pattern in enumerate(patterns):
        match = re.search(pattern, text)
        if match:
            value_group = 2 if idx == 0 else 1
            value = _parse_decimal(match.group(value_group).replace(".", ".").replace(",", "."))
            if value is not None:
                confidence = 0.9 if idx == 0 else 0.7
                return float(value), confidence
    return None, 0.0


def _extract_vat(text: str) -> Tuple[Optional[float], float]:
    match = re.search(r"(?i)\b(vat|tax|gst)\b[^\d]{0,10}([\d]+(?:[\.,]\d{2})?)", text)
    if not match:
        return None, 0.0
    value = _parse_decimal(match.group(2).replace(",", "."))
    if value is None:
        return None, 0.0
    return float(value), 0.8


def _extract_date(text: str) -> Tuple[Optional[str], float]:
    date_like = re.findall(r"\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b|\b\d{1,2}\.\d{1,2}\.\d{2,4}\b", text)
    for item in date_like:
        for fmt in _DATE_PATTERNS:
            try:
                dt = datetime.strptime(item, fmt)
                if dt.year < 2000:
                    continue
                return dt.date().isoformat(), 0.9
            except ValueError:
                continue
    return None, 0.0


def _extract_currency(text: str) -> Tuple[Optional[str], float]:
    symbol_match = re.search(r"[$€£¥]", text)
    if symbol_match:
        return _CURRENCY_SYMBOL_TO_CODE[symbol_match.group(0)], 0.7

    code_match = _CURRENCY_CODE_RE.search(text)
    if code_match:
        return code_match.group(1).upper(), 0.9
    return None, 0.0


def _extract_payment_type(text: str) -> Tuple[Optional[str], float]:
    mapping = {
        "credit card": ["credit", "visa", "mastercard", "amex"],
        "debit card": ["debit"],
        "cash": ["cash"],
        "bank transfer": ["bank transfer", "wire", "iban"],
        "mobile wallet": ["apple pay", "google pay", "gpay"],
    }
    lowered = text.lower()
    for payment_type, keywords in mapping.items():
        if any(keyword in lowered for keyword in keywords):
            return payment_type, 0.8
    return None, 0.0


def _extract_merchant(text: str) -> Tuple[Optional[str], float]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None, 0.0

    bad_tokens = {"receipt", "invoice", "tax", "date", "total", "amount"}
    for line in lines[:6]:
        compact = re.sub(r"[^A-Za-z0-9 &.-]", "", line).strip()
        if len(compact) < 3:
            continue
        if any(token in compact.lower() for token in bad_tokens):
            continue
        return compact, 0.6

    return lines[0][:120], 0.4


# -----------------------------
# Category classification
# -----------------------------


CATEGORY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "train": ("train", "rail", "amtrak", "station", "metro"),
    "flight": ("flight", "airlines", "airway", "boarding", "airport"),
    "taxi": ("taxi", "uber", "lyft", "cab", "ride"),
    "hotel": ("hotel", "inn", "resort", "hostel", "check-in"),
    "meals": ("restaurant", "meal", "dinner", "lunch", "breakfast", "cafe"),
    "parking": ("parking", "garage", "meter", "park"),
    "car_rental": ("rental", "rent-a-car", "hertz", "avis", "enterprise"),
    "fuel": ("fuel", "petrol", "diesel", "gas station", "refuel"),
    "other": tuple(),
}


class ReceiptClassifier:
    def __init__(self, category_keywords: Optional[Dict[str, Iterable[str]]] = None) -> None:
        source = category_keywords or CATEGORY_KEYWORDS
        self.category_keywords = {k: tuple(v) for k, v in source.items()}

    def classify(self, text: str, merchant: Optional[str] = None) -> ClassificationResult:
        corpus = f"{text}\n{merchant or ''}".lower()
        scores: Dict[str, float] = {}
        matched: Dict[str, List[str]] = {}

        for category, keywords in self.category_keywords.items():
            score = 0.0
            hits: List[str] = []
            for kw in keywords:
                if kw in corpus:
                    score += 1.0
                    hits.append(kw)
            if score > 0:
                scores[category] = score
                matched[category] = hits

        if not scores:
            return ClassificationResult(
                suggested_category="other",
                confidence=0.35,
                matched_keywords=[],
            )

        best_category = max(scores.items(), key=lambda item: item[1])[0]
        best_score = scores[best_category]
        total_signals = sum(scores.values())
        confidence = min(0.95, 0.5 + (best_score / max(total_signals, 1.0)) * 0.45)

        return ClassificationResult(
            suggested_category=best_category,
            confidence=round(confidence, 3),
            matched_keywords=matched[best_category],
        )


# -----------------------------
# Pipeline
# -----------------------------


class ReceiptPipeline:
    """Coordinates OCR, field extraction, classification, and audit payload."""

    def __init__(
        self,
        ocr_provider: OCRProvider,
        classifier: Optional[ReceiptClassifier] = None,
        manual_review_threshold: float = 0.65,
    ) -> None:
        self.ocr_provider = ocr_provider
        self.classifier = classifier or ReceiptClassifier()
        self.manual_review_threshold = manual_review_threshold

    def process_upload(self, document: UploadedDocument) -> Dict[str, Any]:
        document.validate()
        raw_text = self.ocr_provider.extract_text(document)
        normalized_text = _normalize_whitespace(raw_text)

        parsed, extraction_confidence = self._extract_fields(raw_text)
        classification = self.classifier.classify(raw_text, parsed.merchant)

        overall_confidence = round((extraction_confidence * 0.65) + (classification.confidence * 0.35), 3)
        requires_review = overall_confidence < self.manual_review_threshold

        audit_record = ReceiptAuditRecord(
            filename=document.filename,
            content_type=document.content_type,
            raw_ocr_text=raw_text,
            parsed_output=parsed,
            suggested_category=classification.suggested_category,
            confidence_score=overall_confidence,
            requires_manual_review=requires_review,
        )

        return {
            "filename": document.filename,
            "content_type": document.content_type,
            "raw_ocr_text": raw_text,
            "normalized_text": normalized_text,
            "parsed_output": asdict(parsed),
            "suggested_category": classification.suggested_category,
            "matched_keywords": classification.matched_keywords,
            "confidence_score": overall_confidence,
            "requires_manual_review": requires_review,
            "audit_record": audit_record.to_dict(),
        }

    def _extract_fields(self, raw_text: str) -> Tuple[ParsedReceipt, float]:
        date, date_conf = _extract_date(raw_text)
        merchant, merchant_conf = _extract_merchant(raw_text)
        total, total_conf = _extract_total(raw_text)
        vat, vat_conf = _extract_vat(raw_text)
        currency, currency_conf = _extract_currency(raw_text)
        payment_type, payment_conf = _extract_payment_type(raw_text)

        parsed = ParsedReceipt(
            date=date,
            merchant=merchant,
            total_amount=total,
            vat=vat,
            currency=currency,
            payment_type=payment_type,
        )

        confidences = [
            date_conf,
            merchant_conf,
            total_conf,
            vat_conf,
            currency_conf,
            payment_conf,
        ]
        non_zero = [score for score in confidences if score > 0]
        extraction_confidence = round(sum(non_zero) / max(len(confidences), 1), 3)
        return parsed, extraction_confidence
