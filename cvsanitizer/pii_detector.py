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
        
        # Email patterns (enhanced with international domains and validation)
        self.email_patterns = [
            # Standard email with international domain support
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?\b',
            # Emails with subdomains and longer TLDs
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,20}\b',
            # Common business email patterns
            r'\b[A-Za-z0-9._%+-]+(?:\.[A-Za-z0-9._%+-]+)*@(?:gmail|yahoo|outlook|hotmail|icloud|protonmail)\.[A-Za-z]{2,}\b',
            # Corporate email patterns (firstname.lastname@company.com)
            r'\b[A-Za-z]+\.[A-Za-z]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
            # Emails with numbers and special characters
            r'\b[A-Za-z0-9]+(?:[._%+-][A-Za-z0-9]+)*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        ]
        
        # Phone patterns by country (enhanced with precise validation)
        self.phone_patterns = {
            'GB': [
                # UK mobile numbers (07xxx xxxxxx or +44 7xxx xxxxxx)
                r'\b(?:\+44\s?7\d{3}\s?\d{6}|07\d{3}\s?\d{6})\b',
                # UK landline numbers with area codes
                r'\b(?:\+44\s?20\d{8}|\+44\s?1\d{9}|\+44\s?2\d{9}|020\d{8}|01\d{9}|02\d{9})\b',
                # UK premium rate numbers
                r'\b(?:\+44\s?9\d{9}|09\d{9})\b',
                # UK free numbers
                r'\b(?:\+44\s?80\d{8}|080\d{8})\b',
            ],
            'US': [
                # US numbers with area code validation
                r'\b\+1[-.\s]?\(?([2-9]\d{2})\)?[-.\s]?([2-9]\d{2})[-.\s]?(\d{4})\b',
                # US numbers without country code
                r'\b([2-9]\d{2})[-.\s]?([2-9]\d{2})[-.\s]?(\d{4})\b',
                # US toll-free numbers
                r'\b\+1[-.\s]?(800|888|877|866|855|844|833)[-.]?(\d{3})[-.\s]?(\d{4})\b',
            ],
            'DE': [
                # German mobile numbers
                r'\b(?:\+49\s?1[5-9]\d{1,2}\s?\d{7,8}|01[5-9]\d{1,2}\s?\d{7,8})\b',
                # German landline numbers with area codes
                r'\b(?:\+49\s?(\d{3,4})\s?(\d{7,8})|0(\d{3,4})\s?(\d{7,8}))\b',
            ],
            'FR': [
                # French mobile numbers
                r'\b(?:\+33\s?6\d{8}|06\d{8})\b',
                # French landline numbers
                r'\b(?:\+33\s?1\d{8}|01\d{8})\b',
            ],
            'CA': [
                # Canadian numbers (similar to US but with specific area codes)
                r'\b\+1[-.\s]?([2-9]\d{2})[-.\s]?(\d{3})[-.\s]?(\d{4})\b',
                r'\b([2-9]\d{2})[-.\s]?(\d{3})[-.\s]?(\d{4})\b',
            ],
            'AU': [
                # Australian mobile numbers
                r'\b(?:\+61\s?4\d{8}|04\d{8})\b',
                # Australian landline numbers
                r'\b(?:\+61\s?[2-8]\d{8}|0[2-8]\d{8})\b',
            ],
        }
        
        # Postcode patterns by country (enhanced with precise validation)
        self.postcode_patterns = {
            'GB': [
                # UK postcode patterns (enhanced)
                r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b',  # Standard format
                r'\b[A-Z]{2}\d{2}\s*\d[A-Z]{2}\b',          # Special cases like SW1A
            ],
            'US': [
                # US ZIP codes
                r'\b\d{5}(?:-\d{4})?\b',                    # 5-digit or ZIP+4
            ],
            'DE': [
                # German postal codes (5 digits)
                r'\b\d{5}\b',
            ],
            'FR': [
                # French postal codes (5 digits)
                r'\b\d{5}\b',
            ],
            'CA': [
                # Canadian postal codes (A1A 1A1)
                r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b',
            ],
            'AU': [
                # Australian postal codes (4 digits)
                r'\b\d{4}\b',
            ],
            'NL': [
                # Dutch postal codes (1234 AB)
                r'\b\d{4}\s?[A-Z]{2}\b',
            ],
            'IT': [
                # Italian postal codes (5 digits)
                r'\b\d{5}\b',
            ],
            'ES': [
                # Spanish postal codes (5 digits)
                r'\b\d{5}\b',
            ],
            'SE': [
                # Swedish postal codes (3-digit or 5-digit)
                r'\b\d{3}\s?\d{2}\b',
            ],
        }
        
        # National ID patterns (enhanced with more countries)
        self.national_id_patterns = {
            'GB': [
                # UK National Insurance Number
                r'\b[A-Z]{2}\d{6}[A-Z]?\b',
            ],
            'US': [
                # US Social Security Number
                r'\b\d{3}-\d{2}-\d{4}\b',
                r'\b\d{3}\s\d{2}\s\d{4}\b',  # Space separated
            ],
            'DE': [
                # German Tax ID (Steuerliche Identifikationsnummer)
                r'\b\d{10,11}\b',
            ],
            'FR': [
                # French INSEE number
                r'\b[1-4]\d{2}(0[1-9]|1[0-2])(?:0[1-9]|[1-3]\d|4[0-8])\d{8}\b',
            ],
            'CA': [
                # Canadian Social Insurance Number
                r'\b\d{3}-\d{3}-\d{3}\b',
            ],
            'AU': [
                # Australian Tax File Number
                r'\b\d{3}\s\d{3}\s\d{3}\b',
                r'\b\d{9}\b',
            ],
            'IT': [
                # Italian Codice Fiscale
                r'\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b',
            ],
            'ES': [
                # Spanish DNI/NIE
                r'\b\d{8}[A-Z]\b',  # DNI
                r'\b[A-Z]\d{7}[A-Z]\b',  # NIE
            ],
            'SE': [
                # Swedish Personal Identity Number
                r'\b\d{6}[-\s]?\d{4}\b',
            ],
        }
        
        # Passport patterns (enhanced with country-specific validation)
        self.passport_patterns = [
            # General passport patterns
            r'\b[A-Z]{1,2}\d{6,9}\b',           # Letter(s) followed by digits
            r'\b\d{8,9}[A-Z]\b',                 # Digits followed by letter
            # Country-specific patterns
            r'\b[A-Z]{2}\d{7}\b',               # US passport format
            r'\b[A-Z]\d{7}[A-Z]\b',              # EU passport format
            r'\b\d{9}[A-Z]{2}\b',               # Some Asian countries
        ]
        
        # Address indicators
        self.address_indicators = [
            'address:', 'lives at', 'residing at', 'location:', 'located at',
            'street', 'st', 'avenue', 'ave', 'road', 'rd', 'lane', 'ln',
            'drive', 'dr', 'court', 'ct', 'way', 'boulevard', 'blvd',
            'apartment', 'apt', 'suite', 'ste', 'unit', 'flat', '#'
        ]
        
        # Social media patterns (enhanced with more platforms)
        self.social_patterns = {
            'linkedin': [
                r'linkedin\.com/in/[A-Za-z0-9\-_]{3,50}',
                r'linkedin\.com/company/[A-Za-z0-9\-_]{3,50}',
                r'linkedin\.com/profile/view\?id=\d+',
            ],
            'twitter': [
                r'twitter\.com/[A-Za-z0-9_]{1,15}',
                r'x\.com/[A-Za-z0-9_]{1,15}',
            ],
            'github': [
                r'github\.com/[A-Za-z0-9\-_]{1,39}',
            ],
            'facebook': [
                r'facebook\.com/[A-Za-z0-9\.\-_/]{5,50}',
                r'fb\.com/[A-Za-z0-9\.\-_/]{5,50}',
            ],
            'instagram': [
                r'instagram\.com/[A-Za-z0-9\._]{1,30}',
            ],
            'youtube': [
                r'youtube\.com/[A-Za-z0-9\-_]{1,50}',
                r'youtu\.be/[A-Za-z0-9\-_]{11}',
            ],
            'tiktok': [
                r'tiktok\.com/@[A-Za-z0-9\._]{1,24}',
            ],
        }
        
        # Name patterns (enhanced with cultural variations)
        self.name_patterns = [
            # Basic Western name patterns
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',                    # First Last
            r'\b[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+\b',          # First M. Last
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',      # First Middle Last
            # Names with hyphens and apostrophes
            r'\b[A-Z][a-zA-Z\-\'\s]+\s+[A-Z][a-zA-Z\-\'\s]+\b',  # Complex names
            # Common name prefixes and suffixes
            r'\b(?:Dr|Mr|Mrs|Ms|Prof|Sir|Lady)\.?\s+[A-Z][a-zA-Z\-\'\s]+\b',
            # International name patterns (simplified)
            r'\b[A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+\b',  # Three-word names
            # Names with special characters (European)
            r'\b[A-Z][a-zA-Záéíóúñü]+\s+[A-Z][a-zA-Záéíóúñü]+\b',
        ]
        
        # Date of birth patterns (enhanced with more formats)
        self.dob_patterns = [
            # Explicit DOB indicators
            r'(?:date of birth|dob|born|birthday)[\s:]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'(?:date of birth|dob|born|birthday)[\s:]*\d{2,4}[/-]\d{1,2}[/-]\d{1,2}',
            # Age-related patterns
            r'(?:age|aged?|years? old)[\s:]*\d{1,2}\s*(?:years?)?\s*(?:old)?',
            r'(?:age|born in)[\s:]*\d{4}',
            # Date formats with context
            r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{2,4}[/-]\d{1,2}[/-]\d{1,2})\s*(?:\(?\d{1,2}\s*(?:years?|y\.o\.)\)?)',
            # International date formats
            r'\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b',  # YYYY-MM-DD
            r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b',  # DD-MM-YYYY or MM-DD-YYYY
            # DOB in personal info sections
            r'(?:personal\s*details?|information|about\s*me|profile)[\s\S]*?(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{2,4}[/-]\d{1,2}[/-]\d{1,2})',
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
        """Detect email addresses with enhanced validation."""
        matches = []
        seen_emails = set()  # Avoid duplicates
        
        for pattern in self.email_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                email = match.group().lower()
                if email not in seen_emails:
                    seen_emails.add(email)
                    # Enhanced confidence scoring
                    confidence = self._calculate_email_confidence(email)
                    matches.append(PIIMatch(
                        category=PIICategory.EMAIL,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=confidence
                    ))
        return matches
    
    def _detect_phones(self, text: str, country: str) -> List[PIIMatch]:
        """Detect phone numbers with country-specific patterns."""
        matches = []
        seen_phones = set()  # Avoid duplicates
        
        # Try country-specific patterns first
        if country in self.phone_patterns:
            patterns = self.phone_patterns[country]
            if isinstance(patterns, list):
                for pattern in patterns:
                    for match in re.finditer(pattern, text):
                        phone = re.sub(r'[^\d+]', '', match.group())
                        if phone not in seen_phones and len(phone) >= 7:
                            seen_phones.add(phone)
                            if self._validate_phone(match.group(), country):
                                confidence = self._calculate_phone_confidence(match.group(), country)
                                matches.append(PIIMatch(
                                    category=PIICategory.PHONE,
                                    text=match.group(),
                                    start=match.start(),
                                    end=match.end(),
                                    confidence=confidence,
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
        """Detect postal codes with country-specific patterns."""
        matches = []
        seen_postcodes = set()  # Avoid duplicates
        
        if country in self.postcode_patterns:
            patterns = self.postcode_patterns[country]
            if isinstance(patterns, list):
                for pattern in patterns:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        postcode = match.group().upper().replace(' ', '')
                        if postcode not in seen_postcodes:
                            seen_postcodes.add(postcode)
                            matches.append(PIIMatch(
                                category=PIICategory.POSTCODE,
                                text=match.group(),
                                start=match.start(),
                                end=match.end(),
                                confidence=0.7,
                                country_code=country
                            ))
            else:
                # Handle string patterns (backward compatibility)
                for match in re.finditer(patterns, text, re.IGNORECASE):
                    postcode = match.group().upper().replace(' ', '')
                    if postcode not in seen_postcodes:
                        seen_postcodes.add(postcode)
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
        """Detect national ID numbers with country-specific patterns."""
        matches = []
        seen_ids = set()  # Avoid duplicates
        
        if country in self.national_id_patterns:
            patterns = self.national_id_patterns[country]
            if isinstance(patterns, list):
                for pattern in patterns:
                    for match in re.finditer(pattern, text):
                        id_text = match.group()
                        if id_text not in seen_ids:
                            seen_ids.add(id_text)
                            matches.append(PIIMatch(
                                category=PIICategory.NATIONAL_ID,
                                text=id_text,
                                start=match.start(),
                                end=match.end(),
                                confidence=0.8,
                                country_code=country
                            ))
            else:
                # Handle string patterns (backward compatibility)
                for match in re.finditer(patterns, text):
                    id_text = match.group()
                    if id_text not in seen_ids:
                        seen_ids.add(id_text)
                        matches.append(PIIMatch(
                            category=PIICategory.NATIONAL_ID,
                            text=id_text,
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
        """Detect social media profiles with enhanced platform support."""
        matches = []
        seen_profiles = set()  # Avoid duplicates
        
        for platform, patterns in self.social_patterns.items():
            if isinstance(patterns, list):
                for pattern in patterns:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        profile = match.group().lower()
                        if profile not in seen_profiles:
                            seen_profiles.add(profile)
                            # Determine category based on platform
                            category = PIICategory.LINKEDIN if platform == 'linkedin' else PIICategory.SOCIAL_MEDIA
                            confidence = self._calculate_social_confidence(match.group(), platform)
                            matches.append(PIIMatch(
                                category=category,
                                text=match.group(),
                                start=match.start(),
                                end=match.end(),
                                confidence=confidence,
                                metadata={'platform': platform}
                            ))
            else:
                # Handle string patterns (backward compatibility)
                for match in re.finditer(patterns, text, re.IGNORECASE):
                    profile = match.group().lower()
                    if profile not in seen_profiles:
                        seen_profiles.add(profile)
                        category = PIICategory.LINKEDIN if platform == 'linkedin' else PIICategory.SOCIAL_MEDIA
                        confidence = self._calculate_social_confidence(match.group(), platform)
                        matches.append(PIIMatch(
                            category=category,
                            text=match.group(),
                            start=match.start(),
                            end=match.end(),
                            confidence=confidence,
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
    
    def _calculate_email_confidence(self, email: str) -> float:
        """Calculate confidence score for email detection."""
        confidence = 0.5  # Base confidence
        
        # Check for common email providers
        common_providers = ['gmail', 'yahoo', 'outlook', 'hotmail', 'icloud', 'protonmail']
        if any(provider in email for provider in common_providers):
            confidence += 0.2
        
        # Check for corporate email patterns
        if '.' in email.split('@')[0] and len(email.split('@')[0].split('.')) >= 2:
            confidence += 0.2
        
        # Check domain validity
        domain = email.split('@')[1] if '@' in email else ''
        if '.' in domain and len(domain.split('.')) >= 2:
            confidence += 0.1
        
        return min(confidence, 0.95)
    
    def _calculate_phone_confidence(self, phone: str, country: str) -> float:
        """Calculate confidence score for phone detection."""
        confidence = 0.6  # Base confidence
        
        # Country-specific validation
        if country == 'GB':
            if phone.startswith('+44') or phone.startswith('0'):
                confidence += 0.2
            if '7' in phone and len(re.sub(r'[^\d]', '', phone)) == 11:  # UK mobile
                confidence += 0.1
        elif country == 'US':
            if phone.startswith('+1') or len(re.sub(r'[^\d]', '', phone)) == 10:
                confidence += 0.2
            if any(code in phone for code in ['800', '888', '877', '866']):  # Toll-free
                confidence += 0.1
        
        # Format validation
        if re.search(r'[\s\-\.\(\)]', phone):  # Proper formatting
            confidence += 0.1
        
        return min(confidence, 0.9)
    
    def _calculate_social_confidence(self, profile: str, platform: str) -> float:
        """Calculate confidence score for social media detection."""
        confidence = 0.7  # Base confidence
        
        # Platform-specific validation
        if platform == 'linkedin':
            if '/in/' in profile:
                confidence += 0.2
            elif '/company/' in profile:
                confidence += 0.1
        elif platform == 'twitter' or platform == 'x':
            username = profile.split('/')[-1] if '/' in profile else profile
            if 1 <= len(username) <= 15:
                confidence += 0.2
        elif platform == 'github':
            username = profile.split('/')[-1] if '/' in profile else profile
            if 1 <= len(username) <= 39:
                confidence += 0.2
        
        # HTTPS protocol
        if profile.startswith('https://'):
            confidence += 0.1
        
        return min(confidence, 0.95)
