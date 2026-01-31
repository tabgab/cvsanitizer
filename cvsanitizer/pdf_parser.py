"""
PDF Parser Module

Handles parsing of PDF files and extracting text content.
Supports multiple PDF parsing libraries for better compatibility.
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import re

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PDFParseError(Exception):
    """Exception raised when PDF parsing fails."""
    pass


class PDFParser:
    """
    PDF parser with fallback support for multiple libraries.
    
    Priority order:
    1. PyMuPDF (fitz) - best quality and speed
    2. pdfplumber - good for complex layouts
    3. PyPDF2 - basic fallback
    """
    
    def __init__(self, preferred_library: str = "auto"):
        """
        Initialize PDF parser.
        
        Args:
            preferred_library: Preferred parsing library ("auto", "pymupdf", "pdfplumber", "pypdf2")
        """
        self.logger = logging.getLogger(__name__)
        self.preferred_library = preferred_library.lower()
        self._check_availability()
    
    def _check_availability(self):
        """Check which PDF libraries are available."""
        available = []
        
        if PYMUPDF_AVAILABLE:
            available.append("pymupdf")
        if PDFPLUMBER_AVAILABLE:
            available.append("pdfplumber")
        if PYPDF2_AVAILABLE:
            available.append("pypdf2")
        
        if not available:
            raise PDFParseError(
                "No PDF parsing library available. Install one of: "
                "PyMuPDF, pdfplumber, or PyPDF2"
            )
        
        self.available_libraries = available
        self.logger.info(f"Available PDF libraries: {available}")
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse PDF file and extract text content.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary containing extracted text and metadata
            
        Raises:
            PDFParseError: If parsing fails
        """
        if not os.path.exists(pdf_path):
            raise PDFParseError(f"PDF file not found: {pdf_path}")
        
        for library in self.available_libraries:
            try:
                if library == "pymupdf":
                    result = self._parse_with_pymupdf(pdf_path)
                elif library == "pdfplumber":
                    result = self._parse_with_pdfplumber(pdf_path)
                elif library == "pypdf2":
                    result = self._parse_with_pypdf2(pdf_path)
                
                # Apply PDF text normalization for better PII detection
                result['text'] = self._normalize_pdf_text(result['text'])
                
                self.logger.info(f"Successfully parsed PDF using {library}")
                return result
                
            except Exception as e:
                self.logger.warning(f"Failed to parse with {library}: {e}")
                continue
        
        raise PDFParseError("All PDF parsing libraries failed")
    
    def _normalize_pdf_text(self, text: str) -> str:
        """
        Normalize PDF text for better PII detection.
        
        This method handles line breaks and text fragmentation issues
        that commonly occur in PDF text extraction.
        
        Args:
            text: Raw extracted text from PDF
            
        Returns:
            Normalized text optimized for PII detection
        """
        if not text:
            return text
        
        # Preserve important structure while fixing fragmentation
        normalized = text
        
        # 1. Fix fragmented phone numbers (digits separated by line breaks)
        normalized = re.sub(r'(\d)\s*\n\s*(\d)', r'\1\2', normalized)
        
        # 2. Fix fragmented addresses (words separated by line breaks)
        normalized = re.sub(r'([a-zA-ZáéíóúñüÁÉÍÓÚÑÜ])\s*\n\s*([a-zA-ZáéíóúñüÁÉÍÓÚÑÜ])', r'\1\2', normalized)
        
        # 3. Fix fragmented email addresses
        normalized = re.sub(r'([a-zA-Z0-9._%+-])\s*\n\s*([a-zA-Z0-9._%+-])', r'\1\2', normalized)
        
        # 4. Fix fragmented URLs and social media
        normalized = re.sub(r'([a-zA-Z0-9\-._/])\s*\n\s*([a-zA-Z0-9\-._/])', r'\1\2', normalized)
        
        # 5. Normalize multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 6. Fix common PDF extraction artifacts
        normalized = re.sub(r'\s*-\s*\n\s*', '', normalized)  # Hyphenated words
        normalized = re.sub(r'\n\s*\n', '\n\n', normalized)  # Preserve paragraph breaks
        
        return normalized.strip()
    
    def _select_library(self) -> str:
        """Select the best available library."""
        if self.preferred_library != "auto":
            if self.preferred_library in self.available_libraries:
                return self.preferred_library
            else:
                self.logger.warning(
                    f"Preferred library {self.preferred_library} not available, "
                    f"falling back to auto selection"
                )
        
        # Auto selection based on availability and quality
        if "pymupdf" in self.available_libraries:
            return "pymupdf"
        elif "pdfplumber" in self.available_libraries:
            return "pdfplumber"
        elif "pypdf2" in self.available_libraries:
            return "pypdf2"
        else:
            raise PDFParseError("No suitable PDF parsing library available")
    
    def _parse_with_pymupdf(self, pdf_path: str) -> Dict[str, Any]:
        """Parse PDF using PyMuPDF (fitz)."""
        if not PYMUPDF_AVAILABLE:
            raise PDFParseError("PyMuPDF not available")
        
        doc = fitz.open(pdf_path)
        
        try:
            text_content = []
            metadata = {}
            
            # Extract metadata
            if doc.metadata:
                metadata.update({
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'subject': doc.metadata.get('subject', ''),
                    'creator': doc.metadata.get('creator', ''),
                    'producer': doc.metadata.get('producer', ''),
                    'creation_date': doc.metadata.get('creationDate', ''),
                    'modification_date': doc.metadata.get('modDate', ''),
                })
            
            # Extract text from each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                
                if page_text.strip():
                    text_content.append({
                        'page': page_num + 1,
                        'text': page_text.strip()
                    })
            
            # Combine all text
            full_text = '\n\n'.join(page['text'] for page in text_content)
            
            return {
                'text': full_text,
                'pages': text_content,
                'metadata': metadata,
                'page_count': len(doc),
                'parser_used': 'pymupdf'
            }
        
        finally:
            doc.close()
    
    def _parse_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Parse PDF using pdfplumber."""
        if not PDFPLUMBER_AVAILABLE:
            raise PDFParseError("pdfplumber not available")
        
        with pdfplumber.open(pdf_path) as pdf:
            text_content = []
            metadata = {}
            
            # Extract metadata
            if hasattr(pdf, 'metadata') and pdf.metadata:
                metadata.update({
                    'title': pdf.metadata.get('Title', ''),
                    'author': pdf.metadata.get('Author', ''),
                    'subject': pdf.metadata.get('Subject', ''),
                    'creator': pdf.metadata.get('Creator', ''),
                    'producer': pdf.metadata.get('Producer', ''),
                    'creation_date': pdf.metadata.get('CreationDate', ''),
                    'modification_date': pdf.metadata.get('ModDate', ''),
                })
            
            # Extract text from each page
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                
                if page_text and page_text.strip():
                    text_content.append({
                        'page': page_num + 1,
                        'text': page_text.strip()
                    })
            
            # Combine all text
            full_text = '\n\n'.join(page['text'] for page in text_content)
            
            return {
                'text': full_text,
                'pages': text_content,
                'metadata': metadata,
                'page_count': len(pdf.pages),
                'parser_used': 'pdfplumber'
            }
    
    def _parse_with_pypdf2(self, pdf_path: str) -> Dict[str, Any]:
        """Parse PDF using PyPDF2."""
        if not PYPDF2_AVAILABLE:
            raise PDFParseError("PyPDF2 not available")
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            text_content = []
            metadata = {}
            
            # Extract metadata
            if hasattr(pdf_reader, 'metadata') and pdf_reader.metadata:
                metadata.update({
                    'title': pdf_reader.metadata.get('/Title', ''),
                    'author': pdf_reader.metadata.get('/Author', ''),
                    'subject': pdf_reader.metadata.get('/Subject', ''),
                    'creator': pdf_reader.metadata.get('/Creator', ''),
                    'producer': pdf_reader.metadata.get('/Producer', ''),
                    'creation_date': pdf_reader.metadata.get('/CreationDate', ''),
                    'modification_date': pdf_reader.metadata.get('/ModDate', ''),
                })
            
            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        text_content.append({
                            'page': page_num + 1,
                            'text': page_text.strip()
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
            
            # Combine all text
            full_text = '\n\n'.join(page['text'] for page in text_content)
            
            return {
                'text': full_text,
                'pages': text_content,
                'metadata': metadata,
                'page_count': len(pdf_reader.pages),
                'parser_used': 'pypdf2'
            }
    
    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get basic information about a PDF file without parsing full content.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with PDF information
        """
        if not os.path.exists(pdf_path):
            raise PDFParseError(f"PDF file not found: {pdf_path}")
        
        file_stat = os.stat(pdf_path)
        
        info = {
            'file_path': pdf_path,
            'file_size': file_stat.st_size,
            'file_size_mb': round(file_stat.st_size / (1024 * 1024), 2),
            'last_modified': file_stat.st_mtime,
        }
        
        # Try to get page count without full parsing
        try:
            library = self._select_library()
            
            if library == "pymupdf":
                doc = fitz.open(pdf_path)
                info['page_count'] = len(doc)
                if doc.metadata:
                    info['metadata'] = {
                        'title': doc.metadata.get('title', ''),
                        'author': doc.metadata.get('author', ''),
                    }
                doc.close()
            
            elif library == "pdfplumber":
                with pdfplumber.open(pdf_path) as pdf:
                    info['page_count'] = len(pdf.pages)
                    if hasattr(pdf, 'metadata') and pdf.metadata:
                        info['metadata'] = {
                            'title': pdf.metadata.get('Title', ''),
                            'author': pdf.metadata.get('Author', ''),
                        }
            
            elif library == "pypdf2":
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    info['page_count'] = len(pdf_reader.pages)
                    if hasattr(pdf_reader, 'metadata') and pdf_reader.metadata:
                        info['metadata'] = {
                            'title': pdf_reader.metadata.get('/Title', ''),
                            'author': pdf_reader.metadata.get('/Author', ''),
                        }
        
        except Exception as e:
            self.logger.warning(f"Failed to get PDF info: {e}")
            info['page_count'] = None
            info['metadata'] = {}
        
        return info
