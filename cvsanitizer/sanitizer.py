"""
Main CV Sanitizer Module

Orchestrates the PII detection, redaction, and output generation process.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .pii_detector import PIIDetector, PIIMatch, PIICategory
from .pdf_parser import PDFParser, PDFParseError


class CVSanitizer:
    """
    Main CV Sanitizer class that coordinates PII detection and redaction.
    
    Workflow:
    1. Parse PDF to extract text
    2. Detect PII using rule-based patterns
    3. Allow user to review and edit detections
    4. Generate redacted output and PII mapping
    5. Save JSON files according to project requirements
    """
    
    def __init__(self, country: str = "GB", pdf_library: str = "auto"):
        """
        Initialize CV Sanitizer.
        
        Args:
            country: Default country code for PII detection
            pdf_library: Preferred PDF parsing library
        """
        self.logger = logging.getLogger(__name__)
        self.country = country.upper()
        self.pdf_parser = PDFParser(preferred_library=pdf_library)
        self.pii_detector = PIIDetector(default_country=country)
        
        # Storage for processing state
        self.current_pdf_path = None
        self.extracted_text = None
        self.detected_pii = []
        self.user_edits = []
        self.redaction_mapping = {}
    
    def load_pdf(self, pdf_path: str) -> Dict[str, any]:
        """
        Load and parse a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with parsing results
            
        Raises:
            PDFParseError: If PDF parsing fails
        """
        self.logger.info(f"Loading PDF: {pdf_path}")
        self.current_pdf_path = Path(pdf_path)
        
        # Parse PDF
        parse_result = self.pdf_parser.parse_pdf(pdf_path)
        self.extracted_text = parse_result['text']
        
        self.logger.info(
            f"Successfully parsed PDF: {parse_result['page_count']} pages, "
            f"{len(self.extracted_text)} characters extracted"
        )
        
        return parse_result
    
    def detect_pii(self, text: Optional[str] = None) -> List[PIIMatch]:
        """
        Detect PII in the extracted text.
        
        Args:
            text: Text to analyze (uses extracted text if not provided)
            
        Returns:
            List of detected PII matches
        """
        if text is None:
            text = self.extracted_text
        
        if not text:
            raise ValueError("No text available for PII detection")
        
        self.logger.info(f"Detecting PII in {len(text)} characters of text")
        self.detected_pii = self.pii_detector.detect_pii(text, self.country)
        
        # Group by category for easier review
        pii_by_category = {}
        for match in self.detected_pii:
            if match.category not in pii_by_category:
                pii_by_category[match.category] = []
            pii_by_category[match.category].append(match)
        
        self.logger.info(f"Detected {len(self.detected_pii)} PII items:")
        for category, matches in pii_by_category.items():
            self.logger.info(f"  - {category.value}: {len(matches)}")
        
        return self.detected_pii
    
    def get_pii_preview(self) -> Dict[str, any]:
        """
        Generate a preview of detected PII for user review.
        
        Returns:
            Dictionary with PII preview information
        """
        if not self.detected_pii:
            return {
                'total_items': 0,
                'by_category': {},
                'text_with_highlights': self.extracted_text,
                'detections': []
            }
        
        # Group by category
        by_category = {}
        for match in self.detected_pii:
            if match.category not in by_category:
                by_category[match.category] = []
            by_category[match.category].append({
                'text': match.text,
                'start': match.start,
                'end': match.end,
                'confidence': match.confidence,
                'country_code': match.country_code,
                'metadata': match.metadata
            })
        
        # Generate highlighted text
        highlighted_text = self._generate_highlighted_text()
        
        return {
            'total_items': len(self.detected_pii),
            'by_category': {cat.value: items for cat, items in by_category.items()},
            'text_with_highlights': highlighted_text,
            'detections': [
                {
                    'id': i,
                    'category': match.category.value,
                    'text': match.text,
                    'start': match.start,
                    'end': match.end,
                    'confidence': match.confidence,
                    'country_code': match.country_code,
                    'metadata': match.metadata
                }
                for i, match in enumerate(self.detected_pii)
            ]
        }
    
    def _generate_highlighted_text(self) -> str:
        """Generate text with PII highlighted for preview."""
        if not self.extracted_text or not self.detected_pii:
            return self.extracted_text
        
        # Sort matches by start position
        sorted_matches = sorted(self.detected_pii, key=lambda x: x.start)
        
        # Build highlighted text
        result = []
        last_pos = 0
        
        for match in sorted_matches:
            # Add text before this match
            result.append(self.extracted_text[last_pos:match.start])
            
            # Add highlighted match (escape brackets for Rich)
            highlighted = f"\\[{match.category.value.upper()}]{match.text}\\[/{match.category.value.upper()}]"
            result.append(highlighted)
            
            last_pos = match.end
        
        # Add remaining text
        result.append(self.extracted_text[last_pos:])
        
        return ''.join(result)
    
    def update_detections(self, updates: List[Dict[str, any]]) -> List[PIIMatch]:
        """
        Update PII detections based on user input.
        
        Args:
            updates: List of updates with 'id', 'action', and optional 'new_text'
                    action can be 'keep', 'remove', or 'edit'
            
        Returns:
            Updated list of PII matches
        """
        updated_matches = []
        
        for update in updates:
            match_id = update.get('id')
            action = update.get('action')
            
            if match_id >= len(self.detected_pii):
                continue
            
            original_match = self.detected_pii[match_id]
            
            if action == 'keep':
                updated_matches.append(original_match)
            elif action == 'remove':
                # Don't add to updated_matches (removes it)
                self.user_edits.append({
                    'type': 'remove',
                    'original_match': original_match,
                    'timestamp': datetime.now().isoformat()
                })
            elif action == 'edit' and 'new_text' in update:
                # Create new match with updated text
                new_match = PIIMatch(
                    category=original_match.category,
                    text=update['new_text'],
                    start=original_match.start,
                    end=original_match.start + len(update['new_text']),
                    confidence=original_match.confidence,
                    country_code=original_match.country_code,
                    metadata=original_match.metadata
                )
                updated_matches.append(new_match)
                
                self.user_edits.append({
                    'type': 'edit',
                    'original_match': original_match,
                    'new_match': new_match,
                    'timestamp': datetime.now().isoformat()
                })
        
        self.detected_pii = updated_matches
        return self.detected_pii
    
    def add_manual_detection(self, category: str, text: str, start: int, end: int) -> PIIMatch:
        """
        Add a manually detected PII item.
        
        Args:
            category: PII category
            text: The PII text
            start: Start position in original text
            end: End position in original text
            
        Returns:
            The created PIIMatch
        """
        try:
            pii_category = PIICategory(category)
        except ValueError:
            raise ValueError(f"Invalid PII category: {category}")
        
        match = PIIMatch(
            category=pii_category,
            text=text,
            start=start,
            end=end,
            confidence=1.0,  # Manual detections have full confidence
            metadata={'source': 'manual'}
        )
        
        self.detected_pii.append(match)
        self.user_edits.append({
            'type': 'add',
            'match': match,
            'timestamp': datetime.now().isoformat()
        })
        
        return match
    
    def generate_redaction(self) -> Tuple[str, Dict[str, str]]:
        """
        Generate redacted text and PII mapping.
        
        Returns:
            Tuple of (redacted_text, pii_mapping)
        """
        if not self.extracted_text or not self.detected_pii:
            raise ValueError("No text or PII detections available")
        
        # Sort matches by start position (reverse order to avoid offset issues)
        sorted_matches = sorted(self.detected_pii, key=lambda x: x.start, reverse=True)
        
        redacted_text = self.extracted_text
        pii_mapping = {}
        
        for i, match in enumerate(sorted_matches, 1):
            # Generate placeholder
            placeholder = f"<pii type=\"{match.category.value}\" serial=\"{i}\">"
            
            # Store mapping
            pii_mapping[placeholder] = {
                'original': match.text,
                'category': match.category.value,
                'position': {'start': match.start, 'end': match.end},
                'confidence': match.confidence,
                'country_code': match.country_code,
                'metadata': match.metadata
            }
            
            # Replace in text
            redacted_text = (
                redacted_text[:match.start] + 
                placeholder + 
                redacted_text[match.end:]
            )
        
        self.redaction_mapping = pii_mapping
        return redacted_text, pii_mapping
    
    def save_outputs(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Save output files according to project requirements.
        
        Args:
            output_dir: Directory to save files (defaults to same as input PDF)
            
        Returns:
            Dictionary with paths to saved files
        """
        if not self.current_pdf_path:
            raise ValueError("No PDF loaded")
        
        if not self.redaction_mapping:
            raise ValueError("No redaction generated. Call generate_redaction() first.")
        
        # Determine output directory
        if output_dir is None:
            output_dir = self.current_pdf_path.parent
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate base filename (without extension)
        base_name = self.current_pdf_path.stem
        
        # Generate redacted text
        redacted_text, _ = self.generate_redaction()
        
        # Save redacted JSON (structured according to models.py)
        redacted_data = {
            'cv_filename': f"{base_name}_redacted.json",
            'original_filename': self.current_pdf_path.name,
            'processing_date': datetime.now().isoformat(),
            'country_code': self.country,
            'parser_used': self.pdf_parser._select_library(),
            'pii_detected_count': len(self.detected_pii),
            'user_edits_count': len(self.user_edits),
            'redacted_text': redacted_text,
            'pii_summary': self._generate_pii_summary(),
            'audit_trail': {
                'user_edits': self.user_edits,
                'processing_timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            }
        }
        
        redacted_path = output_dir / f"{base_name}_redacted.json"
        with open(redacted_path, 'w', encoding='utf-8') as f:
            json.dump(redacted_data, f, indent=2, ensure_ascii=False)
        
        # Save PII mapping file
        pii_path = output_dir / f"{base_name}.pii.json"
        with open(pii_path, 'w', encoding='utf-8') as f:
            json.dump(self.redaction_mapping, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved output files:")
        self.logger.info(f"  - Redacted: {redacted_path}")
        self.logger.info(f"  - PII mapping: {pii_path}")
        
        return {
            'redacted_json': str(redacted_path),
            'pii_mapping_json': str(pii_path)
        }
    
    def _generate_pii_summary(self) -> Dict[str, any]:
        """Generate summary of detected PII."""
        if not self.detected_pii:
            return {'total': 0, 'by_category': {}}
        
        by_category = {}
        for match in self.detected_pii:
            category = match.category.value
            if category not in by_category:
                by_category[category] = 0
            by_category[category] += 1
        
        return {
            'total': len(self.detected_pii),
            'by_category': by_category,
            'confidence_distribution': self._get_confidence_distribution()
        }
    
    def _get_confidence_distribution(self) -> Dict[str, int]:
        """Get distribution of confidence scores."""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for match in self.detected_pii:
            if match.confidence >= 0.8:
                distribution['high'] += 1
            elif match.confidence >= 0.6:
                distribution['medium'] += 1
            else:
                distribution['low'] += 1
        
        return distribution
    
    def get_processing_summary(self) -> Dict[str, any]:
        """Get a summary of the current processing state."""
        return {
            'pdf_loaded': self.current_pdf_path is not None,
            'pdf_path': str(self.current_pdf_path) if self.current_pdf_path else None,
            'text_length': len(self.extracted_text) if self.extracted_text else 0,
            'pii_detected_count': len(self.detected_pii),
            'user_edits_count': len(self.user_edits),
            'country_code': self.country,
            'ready_for_redaction': bool(self.detected_pii),
            'redaction_generated': bool(self.redaction_mapping)
        }
