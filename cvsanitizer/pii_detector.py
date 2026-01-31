"""
Enhanced PII Detection Engine with Localization Support

This module provides rule-based PII detection without using AI.
Supports multiple countries and localization patterns.
"""

import re
import phonenumbers
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PIICategory(Enum):
    """Categories of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    POSTCODE = "postcode"
    NAME = "name"
    DOB = "dob"
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    LINKEDIN = "linkedin"
    WEBSITE = "website"
    SOCIAL_MEDIA = "social_media"


@dataclass
class PIIMatch:
    """Represents a detected PII match."""
    category: PIICategory
    text: str
    start: int
    end: int
    confidence: float
    country_code: Optional[str] = None
    metadata: Optional[Dict] = None


class PIIDetector:
    """
    Enhanced PII detector with localization support.
    
    Features:
    - Multi-country phone number detection
    - Address patterns for different regions
    - National ID formats
    - Name detection with cultural variations
    - Confidence scoring
    """
    
    def __init__(self, default_country: str = "GB"):
        """
        Initialize PII detector.
        
        Args:
            default_country: Default country code for localization
        """
        self.default_country = default_country.upper()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for different PII types."""
        
        # Email patterns (universal)
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\.[A-Z|a-z]{2,}\b',  # .co.uk, .com.au
        ]
        
        # Phone patterns by country
        self.phone_patterns = {
            'GB': [
                r'\b(?:\+44\s?|0)(?:\d\s?){9,10}\b',  # UK mobile/landline
                r'\b(?:\+44\s?|0)7\d{3}\s?\d{6}\b',  # UK mobile specific
                r'\b(?:\+44\s?|0)20\d{4}\s?\d{4}\b',  # London
            ],
            'US': [
                r'\b\+1[-.\s]?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
                r'\b[2-9]\d{2}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            ],
            'DE': [
                r'\b\+49[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b',
                r'\b0\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b',
            ],
            'FR': [
                r'\b\+33[-.\s]?\d{1}[-.\s]?\d{2}[-.\s]?\d{2}[-.\s]?\d{2}[-.\s]?\d{2}\b',
                r'\b0\d{1}[-.\s]?\d{2}[-.\s]?\d{2}[-.\s]?\d{2}[-.\s]?\d{2}\b',
            ],
            'INTL': r'\b\+?[1-9]\d{0,2}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'
        }
        
        # Postcode patterns by country
        self.postcode_patterns = {
            'GB': r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b',
            'US': r'\b\d{5}(?:-\d{4})?\b',
            'DE': r'\b\d{5}\b',
            'FR': r'\b\d{5}\b',
            'CA': r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b',
            'AU': r'\b\d{4}\b',
            'NL': r'\b\d{4}\s?[A-Z]{2}\b',
        }
        
        # National ID patterns
        self.national_id_patterns = {
            'GB': r'\b[A-Z]{2}\d{6}[A-Z]?\b',  # National Insurance
            'US': r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            'DE': r'\b\d{10,11}\b',  # Steuerliche Identifikationsnummer
            'FR': r'\b\d{13}\b',  # Numéro INSEE
        }
        
        # Passport patterns
        self.passport_patterns = [
            r'\b[A-Z]{1,2}\d{6,9}\b',
            r'\b\d{8,9}[A-Z]\b',
        ]
        
        # Address indicators
        self.address_indicators = [
            'address:', 'lives at', 'residing at', 'location:', 'located at',
            'street', 'st', 'avenue', 'ave', 'road', 'rd', 'lane', 'ln',
            'drive', 'dr', 'court', 'ct', 'way', 'boulevard', 'blvd',
            'apartment', 'apt', 'suite', 'ste', 'unit', 'flat', '#'
        ]
        
        # Social media patterns
        self.social_patterns = {
            'linkedin': r'linkedin\.com/in/[A-Za-z0-9\-_]+',
            'twitter': r'twitter\.com/[A-Za-z0-9_]+',
            'github': r'github\.com/[A-Za-z0-9\-_]+',
            'facebook': r'facebook\.com/[A-Za-z0-9\.\-_/]+',
        }
        
        # Name patterns (simplified - would need more sophisticated approach)
        self.name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+\b',  # First M. Last
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Middle Last
        ]
        
        # Date of birth patterns
        self.dob_patterns = [
            r'(?:date of birth|dob|born|birthday)[\s:]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'(?:date of birth|dob|born|birthday)[\s:]*\d{2,4}[/-]\d{1,2}[/-]\d{1,2}',
            r'(?:age|born in)[\s:]*\d{4}',
        ]
    
    def detect_pii(self, text: str, country: Optional[str] = None) -> List[PIIMatch]:
        """
        Detect all PII in the given text.
        
        Args:
            text: Text to analyze
            country: Country code for localization (defaults to default_country)
            
        Returns:
            List of PIIMatch objects
        """
        if country is None:
            country = self.default_country
        
        matches = []
        
        # Detect each PII type
        matches.extend(self._detect_emails(text))
        matches.extend(self._detect_phones(text, country))
        matches.extend(self._detect_postcodes(text, country))
        matches.extend(self._detect_addresses(text))
        matches.extend(self._detect_national_ids(text, country))
        matches.extend(self._detect_passports(text))
        matches.extend(self._detect_social_media(text))
        matches.extend(self._detect_names(text))
        matches.extend(self._detect_dob(text))
        
        # Sort by position and remove duplicates
        matches = sorted(matches, key=lambda x: x.start)
        matches = self._remove_overlaps(matches)
        
        return matches
    
    def _detect_emails(self, text: str) -> List[PIIMatch]:
        """Detect email addresses."""
        matches = []
        for pattern in self.email_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    category=PIICategory.EMAIL,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9
                ))
        return matches
    
    def _detect_phones(self, text: str, country: str) -> List[PIIMatch]:
        """Detect phone numbers with country-specific patterns."""
        matches = []
        
        # Try country-specific patterns first
        if country in self.phone_patterns:
            patterns = self.phone_patterns[country]
            if isinstance(patterns, list):
                for pattern in patterns:
                    for match in re.finditer(pattern, text):
                        # Validate with phonenumbers library if available
                        if self._validate_phone(match.group(), country):
                            matches.append(PIIMatch(
                                category=PIICategory.PHONE,
                                text=match.group(),
                                start=match.start(),
                                end=match.end(),
                                confidence=0.8,
                                country_code=country
                            ))
        
        # Fallback to international pattern
        for match in re.finditer(self.phone_patterns['INTL'], text):
            if self._validate_phone(match.group(), country):
                matches.append(PIIMatch(
                    category=PIICategory.PHONE,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.6,
                    country_code=country
                ))
        
        return matches
    
    def _validate_phone(self, phone: str, country: str) -> bool:
        """Validate phone number using phonenumbers library."""
        try:
            # Clean the phone number
            cleaned = re.sub(r'[^\d+]', '', phone)
            if not cleaned:
                return False
            
            # Parse with phonenumbers
            parsed = phonenumbers.parse(phone, country)
            return phonenumbers.is_valid_number(parsed)
        except:
            # If phonenumbers fails, fall back to basic validation
            cleaned = re.sub(r'[^\d+]', '', phone)
            return len(cleaned) >= 7 and len(cleaned) <= 15
    
    def _detect_postcodes(self, text: str, country: str) -> List[PIIMatch]:
        """Detect postal codes."""
        matches = []
        
        if country in self.postcode_patterns:
            pattern = self.postcode_patterns[country]
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    category=PIICategory.POSTCODE,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.7,
                    country_code=country
                ))
        
        return matches
    
    def _detect_addresses(self, text: str) -> List[PIIMatch]:
        """Detect street addresses."""
        matches = []
        
        # Look for address indicators followed by address-like text
        for indicator in self.address_indicators:
            pattern = rf'{indicator}[\s:]*([^.,\n]+)'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                address_text = match.group(1).strip()
                if self._is_likely_address(address_text):
                    matches.append(PIIMatch(
                        category=PIICategory.ADDRESS,
                        text=address_text,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.6
                    ))
        
        # Look for standalone address patterns
        address_patterns = [
            r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Way|Boulevard|Blvd)\b',
            r'\b\d+\s+[A-Za-z0-9\s]+(?:Apartment|Apt|Suite|Ste|Unit|Flat)\s*#\d+\b',
        ]
        
        for pattern in address_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    category=PIICategory.ADDRESS,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.7
                ))
        
        return matches
    
    def _is_likely_address(self, text: str) -> bool:
        """Check if text is likely to be an address."""
        address_keywords = ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'lane', 'ln']
        has_number = bool(re.search(r'\d+', text))
        has_keyword = any(keyword in text.lower() for keyword in address_keywords)
        return has_number and (has_keyword or len(text.split()) >= 3)
    
    def _detect_national_ids(self, text: str, country: str) -> List[PIIMatch]:
        """Detect national ID numbers."""
        matches = []
        
        if country in self.national_id_patterns:
            pattern = self.national_id_patterns[country]
            for match in re.finditer(pattern, text):
                matches.append(PIIMatch(
                    category=PIICategory.NATIONAL_ID,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.8,
                    country_code=country
                ))
        
        return matches
    
    def _detect_passports(self, text: str) -> List[PIIMatch]:
        """Detect passport numbers."""
        matches = []
        
        for pattern in self.passport_patterns:
            for match in re.finditer(pattern, text):
                # Additional validation for passport format
                if self._is_likely_passport(match.group()):
                    matches.append(PIIMatch(
                        category=PIICategory.PASSPORT,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.7
                    ))
        
        return matches
    
    def _is_likely_passport(self, text: str) -> bool:
        """Check if text is likely a passport number."""
        # Basic validation - passport numbers are typically 8-9 characters
        # and contain letters and numbers
        return 8 <= len(text) <= 9 and re.search(r'[A-Z]', text) and re.search(r'\d', text)
    
    def _detect_social_media(self, text: str) -> List[PIIMatch]:
        """Detect social media profiles."""
        matches = []
        
        for platform, pattern in self.social_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                category = PIICategory.LINKEDIN if platform == 'linkedin' else PIICategory.SOCIAL_MEDIA
                matches.append(PIIMatch(
                    category=category,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.9,
                    metadata={'platform': platform}
                ))
        
        return matches
    
    def _detect_names(self, text: str) -> List[PIIMatch]:
        """Detect person names (simplified approach)."""
        matches = []
        
        # Look for names at the beginning of the document (CV headers)
        lines = text.split('\n')
        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            line = line.strip()
            if not line or '@' in line or re.search(r'\d{3,}', line):
                continue
            
            # Try name patterns
            for pattern in self.name_patterns:
                for match in re.finditer(pattern, line):
                    # Additional validation
                    if self._is_likely_name(match.group(), i == 0):
                        matches.append(PIIMatch(
                            category=PIICategory.NAME,
                            text=match.group(),
                            start=text.find(line) + match.start(),
                            end=text.find(line) + match.end(),
                            confidence=0.5 if i > 0 else 0.8
                        ))
        
        return matches
    
    def _is_likely_name(self, text: str, is_first_line: bool) -> bool:
        """Check if text is likely a person's name."""
        words = text.split()
        
        # Basic validation
        if len(words) < 2 or len(words) > 4:
            return False
        
        # Check if words are capitalized
        capitalized_words = sum(1 for word in words if word and word[0].isupper())
        if capitalized_words < len(words) * 0.7:  # At least 70% capitalized
            return False
        
        # Common non-name words to exclude
        exclude_words = ['curriculum', 'vitae', 'resume', 'cv', 'profile', 'experience']
        if any(word.lower() in exclude_words for word in words):
            return False
        
        return True
    
    def _detect_dob(self, text: str) -> List[PIIMatch]:
        """Detect dates of birth."""
        matches = []
        
        for pattern in self.dob_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    category=PIICategory.DOB,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.8
                ))
        
        return matches
    
    def _remove_overlaps(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove overlapping matches, keeping the one with highest confidence."""
        if not matches:
            return matches
        
        filtered = []
        i = 0
        
        while i < len(matches):
            current = matches[i]
            
            # Check if current overlaps with next matches
            j = i + 1
            overlapping = []
            while j < len(matches) and matches[j].start < current.end:
                overlapping.append(matches[j])
                j += 1
            
            if overlapping:
                # Find the match with highest confidence
                all_matches = [current] + overlapping
                best_match = max(all_matches, key=lambda x: x.confidence)
                filtered.append(best_match)
                i = j  # Skip overlapping matches
            else:
                filtered.append(current)
                i += 1
        
        return filtered
    
    def get_redaction_placeholder(self, match: PIIMatch, serial: int) -> str:
        """Generate a redaction placeholder for a PII match."""
        return f'<pii type="{match.category.value}" serial="{serial}">'
