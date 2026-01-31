# CV Sanitizer

A Python utility to remove personally identifiable information (PII) from CVs before sending them to LLMs or other processing systems.

## Features

- **Rule-based PII Detection** - No AI required for privacy compliance
- **Multi-country Support** - Localized patterns for UK, US, DE, FR, and more
- **Interactive CLI** - Preview and confirm PII detections before redaction
- **Web UI Interface** - Browser-based PII review with visual PDF overlay
- **LLM Processing Consent** - Explicit user agreement before processing
- **PDF Processing** - Support for multiple PDF parsing libraries
- **JSON Output** - Structured output compatible with database models
- **Audit Trail** - Complete tracking of user confirmations and edits
- **Node.js Compatible** - npm package for JavaScript environments
- **AWS Ready** - Serverless deployment with CloudFormation

## Quick Start

### Python Installation

```bash
# Clone the repository
git clone https://github.com/tabgab/cvsanitizer.git
cd cvsanitizer

# Install dependencies
pip install -r requirements.txt

# Run the CLI
python cvsanitize.py your_cv.pdf
```

### Node.js Installation

```bash
# Install from npm
npm install cvsanitizer

# Use in your project
const { sanitizePDF } = require('cvsanitizer');

async function processCV() {
  const result = await sanitizePDF('path/to/cv.pdf', {
    country: 'GB',
    outputDir: './output'
  });
  
  console.log('Redacted CV:', result.redactedJson);
  console.log('PII Mapping:', result.piiMappingJson);
}
```

## Python Usage

### Command Line Interface

```bash
# Basic usage
python cvsanitize.py my_cv.pdf

# With options
python cvsanitize.py my_cv.pdf \
  --output-dir ./output \
  --country GB \
  --pdf-library pymupdf \
  --auto-confirm \
  --ignoreagreement  # Skip LLM consent (testing only)

# Help
python cvsanitize.py --help
```

### Programmatic Usage

```python
from cvsanitizer import CVSanitizer

# Initialize sanitizer
sanitizer = CVSanitizer(country='GB', pdf_library='auto')

# Load and parse PDF
parse_result = sanitizer.load_pdf('my_cv.pdf')

# Detect PII
detections = sanitizer.detect_pii()

# Preview detections
preview = sanitizer.get_pii_preview()
print(f"Found {preview['total_items']} PII items")

# Generate redaction
redacted_text, pii_mapping = sanitizer.generate_redaction()

# Save outputs
output_files = sanitizer.save_outputs('./output')
print(f"Saved: {output_files}")
```

### Interactive Review

The CLI provides an interactive review process:

1. **PII Detection** - Automatically detects PII using rule-based patterns
2. **Preview** - Shows highlighted text with detected PII
3. **Review** - Allows you to keep, remove, or edit detections
4. **LLM Processing Consent** - Explicit agreement for LLM processing
5. **Confirmation** - Final confirmation before processing
6. **Output** - Generates redacted JSON and PII mapping files

### Web UI Interface

For a visual review experience, use the web UI:

```bash
# Start the web UI
cd web-ui
npm install
npm start

# Open browser to http://localhost:3000
```

Web UI features:
- **Custom CV Viewer** - Renders extracted text with inline PII highlighting
- **Interactive Selection** - Click highlighted PII boxes to select/deselect
- **Graphical PII Editing**:
  - **Text Selection** - Select any text and click to add as new PII (Name, Email, Phone, Address, LinkedIn, Nationality, or custom "Other" type)
  - **Drag Handles** - Drag the edges of PII boxes to extend/shrink boundaries
  - **Merge Boxes** - Select multiple adjacent boxes and merge them into one
  - **Delete False Positives** - Remove incorrectly detected PII items
  - **Edit Boundaries** - Modify PII text via edit modal
- **Batch Operations** - Select All, Deselect, Approve All, Approve Selected
- **LLM Consent Modal** - Required agreement before processing
- **Export Results** - Download approved PII as JSON

## Node.js Usage

### Basic API

```javascript
const { CVSanitizer, sanitizePDF, previewPII } = require('cvsanitizer');

// Quick sanitize
async function quickSanitize() {
  const result = await sanitizePDF('cv.pdf', {
    country: 'GB',
    outputDir: './output'
  });
  return result;
}

// Preview PII first
async function previewThenSanitize() {
  const detections = await previewPII('cv.pdf', {
    country: 'GB'
  });
  
  console.log('PII Detections:', detections);
  
  // Proceed with sanitization if satisfied
  const result = await sanitizePDF('cv.pdf');
  return result;
}

// Using the class directly
const sanitizer = new CVSanitizer({ pythonPath: 'python3' });

const result = await sanitizer.sanitizePDF('cv.pdf', {
  country: 'US',
  pdfLibrary: 'pymupdf',
  autoConfirm: true
});
```

### TypeScript Support

```typescript
import { CVSanitizer, SanitizerOptions, PIIDetection } from 'cvsanitizer';

const sanitizer = new CVSanitizer();
const options: SanitizerOptions = {
  country: 'GB',
  outputDir: './output',
  autoConfirm: false
};

const result = await sanitizer.sanitizePDF('cv.pdf', options);
```

## PII Detection

### Supported PII Types

- **Email addresses** - Universal pattern matching
- **Phone numbers** - Country-specific formats (UK, US, DE, FR, etc.)
- **Addresses** - Street addresses and postal codes
- **Names** - Person names (with confidence scoring)
- **Dates of Birth** - Various date formats with context
- **National IDs** - SSN, National Insurance, etc.
- **Passport numbers** - International passport formats
- **Social Media** - LinkedIn, Twitter, GitHub profiles
- **Websites** - Personal websites and portfolios

### Localization Support

```python
# UK format
sanitizer = CVSanitizer(country='GB')

# US format  
sanitizer = CVSanitizer(country='US')

# German format
sanitizer = CVSanitizer(country='DE')

# French format
sanitizer = CVSanitizer(country='FR')
```

### Confidence Scoring

Each PII detection includes a confidence score:

- **High (0.8-1.0)** - Very confident detection
- **Medium (0.6-0.8)** - Likely but needs review
- **Low (0.0-0.6)** - Possible but uncertain

## Output Files

### Redacted JSON (`*_redacted.json`)

```json
{
  "cv_filename": "my_cv_redacted.json",
  "original_filename": "my_cv.pdf",
  "processing_date": "2024-01-01T12:00:00Z",
  "country_code": "GB",
  "parser_used": "pymupdf",
  "pii_detected_count": 3,
  "user_edits_count": 1,
  "redacted_text": "John Doe <pii type=\"email\" serial=\"1\"> has experience...",
  "pii_summary": {
    "total": 3,
    "by_category": {
      "email": 1,
      "phone": 1,
      "address": 1
    }
  },
  "llm_processing_agreement": true,
  "llm_agreement_timestamp": "2024-01-01T12:05:00Z",
  "audit_trail": {
    "user_edits": [...],
    "processing_timestamp": "2024-01-01T12:00:00Z",
    "llm_consent_obtained": true
  }
}
```

### PII Mapping (`*.pii.json`)

```json
{
  "<pii type=\"email\" serial=\"1\">": {
    "original": "john.doe@example.com",
    "category": "email",
    "position": {"start": 8, "end": 26},
    "confidence": 0.9,
    "country_code": "GB"
  }
}
```

## Database Integration

### Audit Trail

The system includes comprehensive audit tracking:

```python
from cvsanitizer.database import CVProcessingSession

# Initialize database session
db_session = CVProcessingSession('sqlite:///cvsanitizer.db')

# Create processing session
session_id = db_session.create_session(
    pdf_path='my_cv.pdf',
    username='john.doe',
    country='GB'
)

# Record PII detections
db_session.record_pii_detection(session_id, detections_list)

# Record user edits
db_session.record_user_edit(session_id, edit_data)

# Record final confirmation
db_session.record_final_confirmation(
    session_id=session_id,
    username='john.doe',
    confirmed=True,
    pii_mapping=pii_mapping,
    output_files=output_files
)
```

### Compatibility with Existing Models

The output format is designed to work with the database schema in `models.py`:

```python
# The redacted JSON can be directly used with UserProfile model
user_profile.cv_text = redacted_data['redacted_text']
user_profile.cv_analysis = redacted_data['pii_summary']
```

## AWS Deployment

### Prerequisites

- AWS CLI configured
- AWS SAM CLI (optional)
- Python 3.8+
- Node.js 14+ (for npm package)

### Quick Deploy

```bash
# Set environment variables
export ENVIRONMENT=dev
export AWS_REGION=us-east-1

# Run deployment script
./aws/deploy.sh
```

### Manual Deployment

```bash
# Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file aws/cloudformation.yaml \
  --stack-name cvsanitizer-dev \
  --parameter-overrides Environment=dev \
  --capabilities CAPABILITY_IAM

# Update Lambda code
aws lambda update-function-code \
  --function-name cvsanitizer-dev \
  --zip-file fileb://deployment.zip
```

### AWS Usage

```bash
# Upload PDF for processing
aws s3 cp my_cv.pdf s3://cvsanitizer-dev-123456789012/uploads/

# Process via API
curl -X POST https://api-id.execute-api.region.amazonaws.com/prod/process \
  -H 'Content-Type: application/json' \
  -d '{"pdf_url": "s3://bucket/uploads/my_cv.pdf"}'

# Download results
aws s3 cp s3://bucket/processed/my_cv_redacted.json ./
aws s3 cp s3://bucket/processed/my_cv.pii.json ./
```

## Configuration

### Environment Variables

```bash
# Python
export CV_SANITIZER_DEFAULT_COUNTRY=GB
export CV_SANITIZER_PDF_LIBRARY=pymupdf
export CV_SANITIZER_DB_URL=sqlite:///cvsanitizer.db

# Node.js
export CV_SANITIZER_PYTHON_PATH=python3
```

### Configuration Files

```python
# config.py
CV_SANITIZER_CONFIG = {
    'default_country': 'GB',
    'pdf_library': 'auto',
    'output_dir': './output',
    'database_url': 'sqlite:///cvsanitizer.db',
    'log_level': 'INFO'
}
```

## Testing

### Python Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=cvsanitizer

# Run specific test
python -m pytest tests/test_pii_detector.py -v
```

### Node.js Tests

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run with coverage
npm run test:coverage
```

### Integration Tests

```bash
# Test with sample PDF
python cvsanitize.py CV_Gabor_Tabi.pdf --auto-confirm

# Test with LLM agreement (normal mode)
python cvsanitize.py CV_Gabor_Tabi.pdf --country HU

# Test with agreement bypass (testing mode)
python cvsanitize.py CV_Gabor_Tabi.pdf --ignoreagreement

# Test Node.js wrapper
node tests/integration.js

# Test Web UI
cd web-ui
npm install
npm start
# Open http://localhost:3000
```

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/tabgab/cvsanitizer.git
cd cvsanitizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Set up Web UI
cd web-ui
npm install
cd ..
```

### Code Style

```bash
# Python formatting
black cvsanitizer/
isort cvsanitizer/

# Linting
flake8 cvsanitizer/
pylint cvsanitizer/

# TypeScript formatting
npm run lint
npm run format
```

### Building npm Package

```bash
# Build TypeScript
npm run build

# Pack for npm
npm pack

# Publish (requires npm login)
npm publish
```

## Troubleshooting

### Common Issues

**PDF Parsing Fails**
```bash
# Try different PDF library
python cvsanitize.py cv.pdf --pdf-library pdfplumber

# Install additional dependencies
pip install pymupdf pdfplumber PyPDF2
```

**PII Detection Not Working**
```bash
# Check country code
python cvsanitize.py cv.pdf --country US

# Verify dependencies
python -c "import phonenumbers; print('phonenumbers available')"
```

**Node.js Wrapper Issues**
```bash
# Check Python path
const sanitizer = new CVSanitizer({ pythonPath: 'python3' });

# Verify dependencies
node -e "console.log(require('child_process').spawnSync('python3', ['--version']))"
```

**LLM Agreement Issues**
```bash
# Bypass agreement for testing
python cvsanitize.py cv.pdf --ignoreagreement

# Check if agreement is recorded
grep "llm_processing_agreement" output/*_redacted.json
```

**Web UI Issues**
```bash
# Check web UI dependencies
cd web-ui && npm install

# Start development server
cd web-ui && npm start

# Clear browser cache if PDF doesn't load
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with debug
python cvsanitize.py cv.pdf --debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Adding New PII Patterns

```python
# In pii_detector.py
class PIIDetector:
    def _compile_patterns(self):
        # Add your new pattern
        self.new_pattern = r'your_regex_here'
```

### Adding New Countries

```python
# Add country-specific patterns
self.phone_patterns['XX'] = [r'country_specific_pattern']
self.postcode_patterns['XX'] = r'country_postcode_pattern'
```

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/tabgab/cvsanitizer/issues)
- **Documentation**: [GitHub Wiki](https://github.com/tabgab/cvsanitizer/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/tabgab/cvsanitizer/discussions)

## Changelog

### v1.1.0 (2026-01-31)
- **Web UI Overhaul** - Complete rewrite with custom CV viewer
  - Graphical PII editing: text selection, drag handles, merge, delete
  - Inline PII highlighting with colored boxes
  - Nationality and custom "Other" PII type support
  - Click outside to deselect, improved UX
- **Improved PII Detection**
  - Full URL detection for LinkedIn and social media (includes https://www.)
  - Auto-merge adjacent address components (street + postcode + city)
  - Single occurrence highlighting (prevents duplicate word redaction)
- **PDF Text Extraction Fixes**
  - Preserved line breaks and document structure
  - Fixed URL joining with section headers
  - Better handling of international characters

### v1.0.0 (2024-01-01)
- Initial release
- PII detection for multiple countries
- Interactive CLI
- Node.js wrapper
- AWS deployment
- Database audit trail

---

**Privacy First**: This tool is designed to protect privacy by removing PII before sending data to external services. No AI is used for PII detection to ensure maximum privacy compliance.
