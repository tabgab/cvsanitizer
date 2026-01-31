# Enhanced PII Detection Patterns - Documentation

## Overview

The CV Sanitizer has been enhanced with sophisticated and powerful PII detection patterns that provide better accuracy, localization support, and confidence scoring.

## Enhanced Features

### 1. Email Detection Improvements

**Previous:** Basic email pattern matching
**Enhanced:** Multi-pattern approach with validation

```python
# Enhanced email patterns
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
```

**Confidence Scoring:**
- Base confidence: 0.5
- +0.2 for common providers (gmail, yahoo, etc.)
- +0.2 for corporate patterns
- +0.1 for valid domain structure
- Maximum: 0.95

### 2. Phone Detection Enhancements

**Previous:** Generic international pattern
**Enhanced:** Country-specific validation with precise formats

```python
# Enhanced phone patterns for UK
'GB': [
    # UK mobile numbers (07xxx xxxxxx or +44 7xxx xxxxxx)
    r'\b(?:\+44\s?7\d{3}\s?\d{6}|07\d{3}\s?\d{6})\b',
    # UK landline numbers with area codes
    r'\b(?:\+44\s?20\d{8}|\+44\s?1\d{9}|\+44\s?2\d{9}|020\d{8}|01\d{9}|02\d{9})\b',
    # UK premium rate numbers
    r'\b(?:\+44\s?9\d{9}|09\d{9})\b',
    # UK free numbers
    r'\b(?:\+44\s?80\d{8}|080\d{8})\b',
]
```

**New Countries Added:**
- Canada (CA): Specific area code validation
- Australia (AU): Mobile and landline patterns
- Enhanced US: Toll-free number detection
- Enhanced Germany: Mobile vs landline distinction
- Enhanced France: Mobile and landline patterns

### 3. Postcode/ZIP Code Improvements

**Previous:** Basic patterns for 6 countries
**Enhanced:** Comprehensive coverage with validation

```python
# Enhanced postcode patterns
self.postcode_patterns = {
    'GB': [
        # UK postcode patterns (enhanced)
        r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b',  # Standard format
        r'\b[A-Z]{2}\d{2}\s*\d[A-Z]{2}\b',          # Special cases like SW1A
    ],
    'NL': [
        # Dutch postal codes (1234 AB)
        r'\b\d{4}\s?[A-Z]{2}\b',
    ],
    # ... additional countries
}
```

**New Countries Added:**
- Netherlands (NL): 1234 AB format
- Italy (IT): 5-digit codes
- Spain (ES): 5-digit codes
- Sweden (SE): 3-digit or 5-digit with space

### 4. National ID Enhancements

**Previous:** 4 countries with basic patterns
**Enhanced:** 9 countries with precise validation

```python
# Enhanced national ID patterns
self.national_id_patterns = {
    'US': [
        # US Social Security Number
        r'\b\d{3}-\d{2}-\d{4}\b',
        r'\b\d{3}\s\d{2}\s\d{4}\b',  # Space separated
    ],
    'FR': [
        # French INSEE number (complex validation)
        r'\b[1-4]\d{2}(0[1-9]|1[0-2])(?:0[1-9]|[1-3]\d|4[0-8])\d{8}\b',
    ],
    'IT': [
        # Italian Codice Fiscale (16 characters)
        r'\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b',
    ],
    # ... additional countries
}
```

**New Countries Added:**
- Canada: Social Insurance Number
- Australia: Tax File Number
- Italy: Codice Fiscale
- Spain: DNI/NIE
- Sweden: Personal Identity Number

### 5. Social Media Platform Expansion

**Previous:** 4 platforms (LinkedIn, Twitter, GitHub, Facebook)
**Enhanced:** 7 platforms with specific validation

```python
# Enhanced social media patterns
self.social_patterns = {
    'linkedin': [
        r'linkedin\.com/in/[A-Za-z0-9\-_]{3,50}',
        r'linkedin\.com/company/[A-Za-z0-9\-_]{3,50}',
        r'linkedin\.com/profile/view\?id=\d+',
    ],
    'twitter': [
        r'twitter\.com/[A-Za-z0-9_]{1,15}',
        r'x\.com/[A-Za-z0-9_]{1,15}',  # X.com support
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
```

**New Platforms Added:**
- Instagram
- YouTube (including youtu.be short links)
- TikTok
- X.com (Twitter rebrand)

### 6. Name Detection Cultural Variations

**Previous:** Basic Western name patterns
**Enhanced:** Cultural variations and special characters

```python
# Enhanced name patterns
self.name_patterns = [
    # Basic Western name patterns
    r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',                    # First Last
    # Names with hyphens and apostrophes
    r'\b[A-Z][a-zA-Z\-\'\s]+\s+[A-Z][a-zA-Z\-\'\s]+\b',  # Complex names
    # Common name prefixes and suffixes
    r'\b(?:Dr|Mr|Mrs|Ms|Prof|Sir|Lady)\.?\s+[A-Z][a-zA-Z\-\'\s]+\b',
    # Names with special characters (European)
    r'\b[A-Z][a-zA-Záéíóúñü]+\s+[A-Z][a-zA-Záéíóúñü]+\b',
]
```

### 7. Date of Birth Context Detection

**Previous:** Basic DOB patterns
**Enhanced:** Context-aware detection with multiple formats

```python
# Enhanced DOB patterns
self.dob_patterns = [
    # Explicit DOB indicators
    r'(?:date of birth|dob|born|birthday)[\s:]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
    # Age-related patterns
    r'(?:age|aged?|years? old)[\s:]*\d{1,2}\s*(?:years?)?\s*(?:old)?',
    # International date formats
    r'\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b',  # YYYY-MM-DD
    r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b',  # DD-MM-YYYY or MM-DD-YYYY
    # DOB in personal info sections
    r'(?:personal\s*details?|information|about\s*me|profile)[\s\S]*?(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{2,4}[/-]\d{1,2}[/-]\d{1,2})',
]
```

## Performance Improvements

### 1. Duplicate Detection
- Added deduplication for emails, phones, postcodes, and social profiles
- Reduces false positives and improves processing efficiency

### 2. Confidence Scoring
- Dynamic confidence calculation based on pattern complexity
- Country-specific validation boosts confidence
- Platform-specific validation for social media

### 3. Pattern Structure
- All patterns now support both list and string formats
- Backward compatibility maintained
- Easier to extend with new patterns

## Test Results

### Before Enhancement
```
PII Detected: 3 items
- email: 1 (confidence: 0.9)
- linkedin: 1 (confidence: 0.9)  
- address: 1 (confidence: 0.7)
```

### After Enhancement
```
PII Detected: 5 items
- email: 1 (confidence: 0.95)      ↑ +0.05
- linkedin: 1 (confidence: 0.90)    ↑ +0.00
- address: 1 (confidence: 0.70)    ↑ +0.00
- dob: 1 (confidence: 0.80)         ↑ NEW
- name: 1 (confidence: 0.50)        ↑ NEW
```

## Platform Compatibility

### Python
✅ Fully compatible - Enhanced patterns integrated seamlessly

### Node.js
✅ Fully compatible - Python wrapper processes enhanced patterns

### AWS
✅ Fully compatible - Lambda function uses enhanced detection

## Usage Examples

### Enhanced Country Support
```python
# Canadian CV
detector = PIIDetector(country='CA')
detections = detector.detect_pii(cv_text)

# Australian CV  
detector = PIIDetector(country='AU')
detections = detector.detect_pii(cv_text)
```

### Confidence-based Filtering
```python
detector = PIIDetector()
detections = detector.detect_pii(text)

# Filter high-confidence detections only
high_confidence = [d for d in detections if d.confidence >= 0.8]
```

### Platform-specific Social Media Detection
```python
# Detect multiple platforms
detections = detector.detect_pii(text)
social_profiles = [d for d in detections if d.category == PIICategory.SOCIAL_MEDIA]

# Check platform metadata
for detection in social_profiles:
    platform = detection.metadata.get('platform')
    print(f"Found {platform} profile: {detection.text}")
```

## Future Enhancements

1. **Machine Learning Integration**: Optional ML-based validation for edge cases
2. **Custom Pattern Loading**: JSON-based pattern configuration
3. **Real-time Validation**: API-based validation for phone numbers and emails
4. **Multilingual Support**: Pattern support for non-Latin scripts
5. **Context-aware Detection**: Advanced context analysis for better accuracy

## Migration Guide

No breaking changes introduced. Existing code continues to work with enhanced accuracy automatically.

For new features:
```python
# Use new countries
detector = PIIDetector(country='CA')  # Canada
detector = PIIDetector(country='AU')  # Australia

# Access confidence scores
for detection in detector.detect_pii(text):
    print(f"PII: {detection.text}, Confidence: {detection.confidence}")
```
