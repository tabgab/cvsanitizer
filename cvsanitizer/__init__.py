"""
CV Sanitizer - PII Detection and Redaction for CVs

A Python utility to remove personally identifiable information (PII) from CVs
before sending them to LLMs or other processing systems.

Features:
- PDF parsing and text extraction
- Rule-based PII detection (no AI required)
- Localization support for multiple countries
- Interactive preview and confirmation
- Reversible redaction with mapping storage
- JSON output compatible with database models
"""

__version__ = "1.0.0"
__author__ = "CV Sanitizer Team"

from .sanitizer import CVSanitizer
from .pii_detector import PIIDetector
from .pdf_parser import PDFParser

__all__ = [
    "CVSanitizer",
    "PIIDetector", 
    "PDFParser",
]
