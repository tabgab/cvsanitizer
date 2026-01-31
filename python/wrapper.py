#!/usr/bin/env python3
"""
Python Wrapper for CV Sanitizer Node.js Integration

This script provides a JSON-based interface for the Node.js wrapper
to communicate with the CV Sanitizer Python library.
"""

import sys
import json
import argparse
from pathlib import Path

# Add the parent directory to Python path to import cvsanitizer
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from cvsanitizer.sanitizer import CVSanitizer
    from cvsanitizer.pdf_parser import PDFParser
    CV_SANITIZER_AVAILABLE = True
except ImportError as e:
    CV_SANITIZER_AVAILABLE = False
    IMPORT_ERROR = str(e)


def main():
    """Main wrapper function."""
    parser = argparse.ArgumentParser(description='CV Sanitizer Python Wrapper')
    parser.add_argument('pdf_path', help='Path to PDF file')
    parser.add_argument('--country', default='GB', help='Country code for PII detection')
    parser.add_argument('--pdf-library', default='auto', help='PDF parsing library')
    parser.add_argument('--output-dir', help='Output directory')
    parser.add_argument('--auto-confirm', action='store_true', help='Skip interactive confirmation')
    parser.add_argument('--preview-only', action='store_true', help='Only preview PII detections')
    parser.add_argument('--info-only', action='store_true', help='Only get PDF info')
    parser.add_argument('--check-deps', action='store_true', help='Check dependencies')
    
    args = parser.parse_args()
    
    try:
        # Handle dependency check
        if args.check_deps:
            result = check_dependencies()
            print(json.dumps(result))
            return
        
        # Check if CV Sanitizer is available
        if not CV_SANITIZER_AVAILABLE:
            result = {
                'success': False,
                'error': 'CV Sanitizer not available',
                'details': IMPORT_ERROR
            }
            print(json.dumps(result))
            return
        
        # Handle PDF info request
        if args.info_only:
            result = get_pdf_info(args.pdf_path, args.pdf_library)
            print(json.dumps(result))
            return
        
        # Initialize sanitizer
        sanitizer = CVSanitizer(country=args.country, pdf_library=args.pdf_library)
        
        # Load PDF
        parse_result = sanitizer.load_pdf(args.pdf_path)
        
        # Detect PII
        detections = sanitizer.detect_pii()
        
        # Handle preview only
        if args.preview_only:
            preview = sanitizer.get_pii_preview()
            result = {
                'success': True,
                'detections': preview['detections'],
                'total_items': preview['total_items'],
                'by_category': preview['by_category']
            }
            print(json.dumps(result))
            return
        
        # Generate redaction
        redacted_text, pii_mapping = sanitizer.generate_redaction()
        
        # Save outputs
        output_files = sanitizer.save_outputs(args.output_dir)
        
        # Generate summary
        summary = {
            'total_items': len(pii_mapping),
            'by_category': {},
            'processing_time': 0  # Could add timing if needed
        }
        
        for placeholder, info in pii_mapping.items():
            category = info['category']
            if category not in summary['by_category']:
                summary['by_category'][category] = 0
            summary['by_category'][category] += 1
        
        # Return result
        result = {
            'success': True,
            'redacted_json': output_files['redacted_json'],
            'pii_mapping_json': output_files['pii_mapping_json'],
            'summary': summary,
            'pdf_info': {
                'page_count': parse_result['page_count'],
                'text_length': len(parse_result['text']),
                'parser_used': parse_result['parser_used']
            }
        }
        
        print(json.dumps(result))
    
    except Exception as e:
        result = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
        print(json.dumps(result))
        sys.exit(1)


def check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    
    # Check core dependencies
    try:
        import cvsanitizer
    except ImportError:
        missing_deps.append('cvsanitizer')
    
    # Check PDF parsing libraries
    pdf_libs = ['PyMuPDF', 'pdfplumber', 'PyPDF2']
    available_libs = []
    
    for lib in pdf_libs:
        try:
            if lib == 'PyMuPDF':
                import fitz
                available_libs.append('pymupdf')
            elif lib == 'pdfplumber':
                import pdfplumber
                available_libs.append('pdfplumber')
            elif lib == 'PyPDF2':
                import PyPDF2
                available_libs.append('pypdf2')
        except ImportError:
            missing_deps.append(lib.lower())
    
    # Check other dependencies
    other_deps = ['phonenumbers', 'click', 'rich']
    for dep in other_deps:
        try:
            __import__(dep)
        except ImportError:
            missing_deps.append(dep)
    
    return {
        'available': len(missing_deps) == 0,
        'missing_deps': missing_deps,
        'available_pdf_libs': available_libs,
        'recommendation': 'Install missing dependencies with: pip install -r requirements.txt' if missing_deps else 'All dependencies available'
    }


def get_pdf_info(pdf_path: str, pdf_library: str = 'auto'):
    """Get PDF file information."""
    try:
        parser = PDFParser(preferred_library=pdf_library)
        info = parser.get_pdf_info(pdf_path)
        
        return {
            'success': True,
            'file_info': info
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }


if __name__ == '__main__':
    main()
