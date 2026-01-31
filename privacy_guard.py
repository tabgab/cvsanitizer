"""
Privacy Guard - PII Detection and Redaction for CV Data.
Ensures personal information is removed before sending to LLMs.

This module provides:
1. PII detection (phone, email, address, DOB, names)
2. Redaction with reversible mapping
3. Automatic restoration for final documents
4. Transparency logging of what was redacted
"""

import re
import hashlib
from typing import Tuple
from dataclasses import dataclass, field


@dataclass
class RedactionResult:
    """Result of PII redaction with mapping for restoration."""
    redacted_text: str
    mapping: dict = field(default_factory=dict)
    redacted_items: list = field(default_factory=list)
    
    def add_redaction(self, original: str, placeholder: str, pii_type: str):
        """Track a redaction for potential restoration."""
        self.mapping[placeholder] = original
        self.redacted_items.append({
            'type': pii_type,
            'original': original[:3] + '***',  # Partially masked for logs
            'placeholder': placeholder
        })


class PrivacyGuard:
    """
    Privacy-first PII handler for CV data.
    
    Usage:
        guard = PrivacyGuard()
        result = guard.redact(cv_text)
        
        # Send result.redacted_text to LLM
        # Later, restore with:
        final_text = guard.restore(llm_output, result.mapping)
    """
    
    # Regex patterns for PII detection
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone_uk': r'\b(?:\+44\s?|0)(?:\d\s?){9,10}\b',
        'phone_intl': r'\b\+?[1-9]\d{0,2}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b',
        'postcode_uk': r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b',
        'postcode_us': r'\b\d{5}(?:-\d{4})?\b',
        'dob': r'\b(?:\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{2,4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b',
        'ssn_uk': r'\b[A-Z]{2}\d{6}[A-Z]?\b',  # National Insurance Number
        'passport': r'\b[A-Z]{1,2}\d{6,9}\b',
        'linkedin': r'linkedin\.com/in/[A-Za-z0-9\-_]+',
        'address_line': r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Way|Boulevard|Blvd)\b',
    }
    
    # Words that often appear before addresses
    ADDRESS_INDICATORS = ['address:', 'lives at', 'residing at', 'location:']
    
    def __init__(self, preserve_name: bool = True):
        """
        Initialize Privacy Guard.
        
        Args:
            preserve_name: If True, names are kept but other PII is redacted.
                          Names are needed for CV generation. Set False for
                          maximum anonymization.
        """
        self.preserve_name = preserve_name
        self._name_cache = None
    
    def redact(self, text: str, extract_name: bool = True) -> RedactionResult:
        """
        Redact PII from text.
        
        Args:
            text: The CV or document text to redact
            extract_name: If True, try to extract and preserve the name
            
        Returns:
            RedactionResult with redacted text and restoration mapping
        """
        result = RedactionResult(redacted_text=text)
        
        # Extract name first (usually at the top of CV)
        if extract_name and self.preserve_name:
            name = self._extract_name(text)
            if name:
                self._name_cache = name
                result.mapping['[CANDIDATE_NAME]'] = name
        
        # Redact each PII type
        result.redacted_text = self._redact_emails(result)
        result.redacted_text = self._redact_phones(result)
        result.redacted_text = self._redact_addresses(result)
        result.redacted_text = self._redact_dates(result)
        result.redacted_text = self._redact_ids(result)
        result.redacted_text = self._redact_urls(result)
        
        return result
    
    def _extract_name(self, text: str) -> str:
        """
        Extract the person's name from the CV.
        Usually the first line or prominently placed.
        """
        lines = text.strip().split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            # Skip empty lines, emails, phones
            if not line or '@' in line or re.search(r'\d{3,}', line):
                continue
            # Name is usually short (2-4 words) and title-case
            words = line.split()
            if 2 <= len(words) <= 4:
                # Check if it looks like a name (capitalized words)
                if all(word[0].isupper() for word in words if word):
                    return line
        return None
    
    def _redact_emails(self, result: RedactionResult) -> str:
        """Redact email addresses."""
        text = result.redacted_text
        
        for match in re.finditer(self.PATTERNS['email'], text, re.IGNORECASE):
            email = match.group()
            placeholder = '[EMAIL_REDACTED]'
            result.add_redaction(email, placeholder, 'email')
            text = text.replace(email, placeholder, 1)
        
        return text
    
    def _redact_phones(self, result: RedactionResult) -> str:
        """Redact phone numbers."""
        text = result.redacted_text
        
        # UK format first (more specific)
        for match in re.finditer(self.PATTERNS['phone_uk'], text):
            phone = match.group()
            placeholder = '[PHONE_REDACTED]'
            result.add_redaction(phone, placeholder, 'phone')
            text = text.replace(phone, placeholder, 1)
        
        # International format
        for match in re.finditer(self.PATTERNS['phone_intl'], text):
            phone = match.group()
            if '[PHONE_REDACTED]' not in phone:  # Don't re-redact
                placeholder = '[PHONE_REDACTED]'
                result.add_redaction(phone, placeholder, 'phone')
                text = text.replace(phone, placeholder, 1)
        
        return text
    
    def _redact_addresses(self, result: RedactionResult) -> str:
        """Redact postal addresses and postcodes."""
        text = result.redacted_text
        
        # UK Postcodes
        for match in re.finditer(self.PATTERNS['postcode_uk'], text, re.IGNORECASE):
            postcode = match.group()
            placeholder = '[POSTCODE_REDACTED]'
            result.add_redaction(postcode, placeholder, 'postcode')
            text = text.replace(postcode, placeholder, 1)
        
        # US ZIP codes (be careful - could match other numbers)
        # Only redact if near address indicators
        for indicator in self.ADDRESS_INDICATORS:
            if indicator.lower() in text.lower():
                for match in re.finditer(self.PATTERNS['postcode_us'], text):
                    zipcode = match.group()
                    placeholder = '[ZIP_REDACTED]'
                    result.add_redaction(zipcode, placeholder, 'zipcode')
                    text = text.replace(zipcode, placeholder, 1)
                break
        
        # Street addresses
        for match in re.finditer(self.PATTERNS['address_line'], text, re.IGNORECASE):
            address = match.group()
            placeholder = '[ADDRESS_REDACTED]'
            result.add_redaction(address, placeholder, 'address')
            text = text.replace(address, placeholder, 1)
        
        return text
    
    def _redact_dates(self, result: RedactionResult) -> str:
        """Redact dates that could be DOB (not employment dates)."""
        text = result.redacted_text
        
        # Look for DOB indicators
        dob_patterns = [
            r'(?:date of birth|dob|born|birthday)[\s:]*' + self.PATTERNS['dob'],
            r'(?:age|born in)[\s:]*\d{4}',
        ]
        
        for pattern in dob_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                dob = match.group()
                placeholder = '[DOB_REDACTED]'
                result.add_redaction(dob, placeholder, 'dob')
                text = text.replace(dob, placeholder, 1)
        
        return text
    
    def _redact_ids(self, result: RedactionResult) -> str:
        """Redact ID numbers (NI numbers, passport, etc.)."""
        text = result.redacted_text
        
        # UK National Insurance Number
        for match in re.finditer(self.PATTERNS['ssn_uk'], text):
            ni = match.group()
            placeholder = '[NI_REDACTED]'
            result.add_redaction(ni, placeholder, 'ni_number')
            text = text.replace(ni, placeholder, 1)
        
        return text
    
    def _redact_urls(self, result: RedactionResult) -> str:
        """Redact personal URLs like LinkedIn (keep GitHub for devs)."""
        text = result.redacted_text
        
        # LinkedIn profiles
        for match in re.finditer(self.PATTERNS['linkedin'], text, re.IGNORECASE):
            url = match.group()
            placeholder = '[LINKEDIN_REDACTED]'
            result.add_redaction(url, placeholder, 'linkedin')
            text = text.replace(url, placeholder, 1)
        
        return text
    
    def restore(self, text: str, mapping: dict) -> str:
        """
        Restore redacted PII in output text.
        
        Args:
            text: Text with redaction placeholders
            mapping: The mapping from RedactionResult
            
        Returns:
            Text with original PII restored
        """
        restored = text
        for placeholder, original in mapping.items():
            restored = restored.replace(placeholder, original)
        return restored
    
    def get_redaction_summary(self, result: RedactionResult) -> dict:
        """
        Get a summary of what was redacted for user transparency.
        
        Returns:
            Dictionary with counts and types of redacted items
        """
        summary = {
            'total_redactions': len(result.redacted_items),
            'by_type': {},
            'items': result.redacted_items
        }
        
        for item in result.redacted_items:
            pii_type = item['type']
            summary['by_type'][pii_type] = summary['by_type'].get(pii_type, 0) + 1
        
        return summary


def redact_for_llm(text: str, preserve_name: bool = True) -> Tuple[str, dict]:
    """
    Convenience function to redact text before sending to LLM.
    
    Args:
        text: CV or document text
        preserve_name: Whether to keep the person's name
        
    Returns:
        Tuple of (redacted_text, mapping_for_restoration)
    """
    guard = PrivacyGuard(preserve_name=preserve_name)
    result = guard.redact(text)
    
    print(f"[PRIVACY] Redacted {len(result.redacted_items)} PII items")
    for item in result.redacted_items:
        print(f"  - {item['type']}: {item['original']}")
    
    return result.redacted_text, result.mapping


def restore_pii(text: str, mapping: dict) -> str:
    """
    Convenience function to restore PII after LLM processing.
    
    Args:
        text: LLM output with placeholders
        mapping: Mapping from redact_for_llm
        
    Returns:
        Text with PII restored
    """
    guard = PrivacyGuard()
    return guard.restore(text, mapping)
