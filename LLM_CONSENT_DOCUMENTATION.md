# LLM Processing Consent Mechanism

## Overview

The CV Sanitizer now includes a mandatory LLM processing consent mechanism to ensure users explicitly agree to submit their personal information for LLM processing after reviewing what will be redacted.

## Consent Workflow

### 1. PII Detection and Review
- System detects PII in the CV using rule-based patterns
- User can review detected PII items via CLI or Web UI
- User can approve, remove, or modify PII detections

### 2. LLM Processing Agreement
- Before final processing, user must explicitly consent to LLM processing
- Consent message: "I have reviewed what personal information will be redacted before LLM processing and concede to submit the remaining information to LLM processing."
- User can choose "Agree" or "Reject"

### 3. Processing Continuation
- If user agrees: Processing continues and agreement is recorded
- If user rejects: Process is terminated and no files are saved
- Agreement status is stored in output JSON files

## Implementation Details

### CLI Implementation

The CLI includes an interactive consent step:

```bash
# Normal mode (requires consent)
python cvsanitize.py my_cv.pdf

# Testing mode (bypasses consent)
python cvsanitize.py my_cv.pdf --ignoreagreement
```

### Web UI Implementation

The Web UI provides a modal dialog:

```javascript
// Consent modal appears when user clicks "Approve All"
{
  title: "LLM Processing Consent",
  message: "I have reviewed what personal information will be redacted before LLM processing and concede to submit the remaining information to LLM processing.",
  options: ["Agree", "Reject"]
}
```

### JSON Output Structure

The consent information is stored in the redacted JSON:

```json
{
  "llm_processing_agreement": true,
  "llm_agreement_timestamp": "2024-01-31T16:20:00Z",
  "audit_trail": {
    "llm_consent_obtained": true,
    "user_edits": [...]
  }
}
```

## Security and Compliance

### Data Protection
- No data is processed without explicit consent
- Consent status is immutably recorded in audit trail
- Users can reject consent at any time before processing

### Audit Trail
- Complete record of consent decisions
- Timestamp of consent agreement
- Integration with existing audit trail system

### Testing Mode
- `--ignoreagreement` flag for development/testing
- Clearly marked as testing-only in documentation
- Agreement recorded as "bypassed for testing" in audit trail

## User Experience

### CLI Flow
1. PII detection and preview
2. Interactive review (optional)
3. LLM processing consent prompt
4. Final confirmation
5. File generation

### Web UI Flow
1. PDF display with PII overlays
2. Interactive selection/approval
3. "Approve All" triggers consent modal
4. Agreement verification
5. Results download

## Error Handling

### Consent Rejection
- Process terminates immediately
- No files are saved
- User can restart with different PII selections

### Missing Consent
- System prevents processing without consent
- Clear error message explaining requirement
- Guidance on how to provide consent

## Integration Points

### Database Models
- Consent status integrated with UserProfile model
- Audit trail extends existing tracking system

### API Integration
- Consent status included in API responses
- Webhook notifications for consent events

### Third-party Systems
- Consent data available for compliance reporting
- Integration with privacy management systems

## Configuration

### Environment Variables
```bash
# Enable testing mode (development only)
CV_SANITIZER_BYPASS_CONSENT=true

# Custom consent message
CV_SANITIZER_CONSENT_MESSAGE="Custom consent text"
```

### Configuration Files
```python
CV_SANITIZER_CONFIG = {
    'require_llm_consent': True,
    'consent_message': "I have reviewed...",
    'allow_bypass': False  # Set to True only for testing
}
```

## Monitoring and Analytics

### Consent Metrics
- Consent rate (accepted vs rejected)
- Time to consent
- PII review time before consent

### Compliance Reporting
- Consent audit logs
- Processing completion rates
- User satisfaction metrics

## Future Enhancements

### Advanced Consent Options
- Granular consent for different PII types
- Time-limited consent
- Revocable consent

### Integration Features
- SSO integration for consent tracking
- Multi-language consent messages
- Accessibility improvements

### Compliance Features
- GDPR compliance reporting
- Data retention policies
- Right to be forgotten implementation

## Troubleshooting

### Common Issues

**Consent not recorded**
```bash
# Check JSON output for consent fields
grep "llm_processing_agreement" output/*_redacted.json

# Verify audit trail
grep "llm_consent_obtained" output/*_redacted.json
```

**Testing mode not working**
```bash
# Ensure flag is correctly used
python cvsanitize.py cv.pdf --ignoreagreement --verbose

# Check for permission issues
ls -la output/
```

**Web UI consent modal not appearing**
```bash
# Check browser console for errors
# Verify JavaScript is enabled
# Clear browser cache and reload
```

### Debug Mode
```bash
# Enable verbose logging
python cvsanitize.py cv.pdf --debug --verbose

# Check consent flow
python cvsanitize.py cv.pdf --debug 2>&1 | grep -i consent
```

## Best Practices

### Development
- Always test with `--ignoreagreement` during development
- Never use bypass mode in production
- Include consent testing in CI/CD pipeline

### Production
- Monitor consent rates and user feedback
- Regular audit of consent records
- Update consent messages as required

### User Support
- Provide clear instructions for consent process
- Offer help for users who reject consent
- Document consent requirements clearly
