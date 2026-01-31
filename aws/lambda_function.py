#!/usr/bin/env python3
"""
AWS Lambda Function for CV Sanitizer

This Lambda function processes PDF files uploaded to S3 and returns
redacted JSON files with PII removed.
"""

import json
import boto3
import os
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote_plus
from datetime import datetime

# Initialize AWS clients
s3_client = boto3.client('s3')

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
S3_BUCKET = os.environ.get('S3_BUCKET')
PYTHON_VERSION = os.environ.get('PYTHON_VERSION', 'python3.9')

def lambda_handler(event, context):
    """
    Main Lambda handler for processing CV files.
    
    This function handles both S3 events (automatic processing) and
    direct API calls (manual processing).
    """
    try:
        print(f"CV Sanitizer Lambda invoked - Environment: {ENVIRONMENT}")
        
        # Determine event type
        if 'Records' in event:
            # S3 event
            return handle_s3_event(event, context)
        elif 'body' in event:
            # API Gateway event
            return handle_api_event(event, context)
        else:
            raise ValueError("Unsupported event type")
    
    except Exception as e:
        print(f"Error in Lambda handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

def handle_s3_event(event, context):
    """Handle S3 file upload events."""
    print("Processing S3 event")
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        # Only process PDF files
        if not key.lower().endswith('.pdf'):
            print(f"Skipping non-PDF file: {key}")
            continue
        
        print(f"Processing file: s3://{bucket}/{key}")
        
        # Download PDF from S3
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            s3_client.download_file(bucket, key, temp_file.name)
            pdf_path = temp_file.name
        
        try:
            # Process CV
            result = process_cv_file(pdf_path, key)
            
            # Upload results back to S3
            base_name = Path(key).stem
            redacted_key = f'processed/{base_name}_redacted.json'
            pii_key = f'processed/{base_name}.pii.json'
            
            # Upload redacted JSON
            s3_client.put_object(
                Bucket=bucket,
                Key=redacted_key,
                Body=json.dumps(result['redacted_data'], indent=2).encode(),
                ContentType='application/json',
                Metadata={
                    'original_file': key,
                    'processed_at': datetime.now().isoformat(),
                    'environment': ENVIRONMENT
                }
            )
            
            # Upload PII mapping
            s3_client.put_object(
                Bucket=bucket,
                Key=pii_key,
                Body=json.dumps(result['pii_mapping'], indent=2).encode(),
                ContentType='application/json',
                Metadata={
                    'original_file': key,
                    'processed_at': datetime.now().isoformat(),
                    'environment': ENVIRONMENT
                }
            )
            
            print(f"Successfully processed {key}")
            print(f"Redacted file: s3://{bucket}/{redacted_key}")
            print(f"PII mapping: s3://{bucket}/{pii_key}")
        
        finally:
            # Clean up temporary file
            os.unlink(pdf_path)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'CV processing completed successfully',
            'timestamp': datetime.now().isoformat()
        })
    }

def handle_api_event(event, context):
    """Handle direct API calls for manual processing."""
    print("Processing API event")
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        if 'pdf_url' not in body:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required field: pdf_url'
                })
            }
        
        pdf_url = body['pdf_url']
        options = body.get('options', {})
        
        # Download PDF from URL (placeholder - would need implementation)
        # For now, assume it's already in S3
        if pdf_url.startswith('s3://'):
            # Parse S3 URL
            pdf_path = download_from_s3(pdf_url)
        else:
            raise ValueError("Only S3 URLs are supported")
        
        try:
            # Process CV
            result = process_cv_file(pdf_path, 'manual_upload.pdf')
            
            # Generate response
            response_data = {
                'success': True,
                'redacted_data': result['redacted_data'],
                'pii_mapping': result['pii_mapping'],
                'processing_info': {
                    'timestamp': datetime.now().isoformat(),
                    'environment': ENVIRONMENT,
                    'pii_count': len(result['pii_mapping'])
                }
            }
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(response_data)
            }
        
        finally:
            # Clean up
            if 'pdf_path' in locals():
                os.unlink(pdf_path)
    
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }

def download_from_s3(s3_url):
    """Download file from S3 URL."""
    # Parse s3://bucket/key format
    if not s3_url.startswith('s3://'):
        raise ValueError("Invalid S3 URL format")
    
    parts = s3_url[5:].split('/', 1)
    if len(parts) != 2:
        raise ValueError("Invalid S3 URL format")
    
    bucket, key = parts
    
    # Download to temporary file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        s3_client.download_file(bucket, key, temp_file.name)
        return temp_file.name

def process_cv_file(pdf_path, original_filename):
    """
    Process a CV file using the CV Sanitizer library.
    
    This is a placeholder implementation. In a real deployment,
    you would need to package the CV Sanitizer library with the Lambda.
    """
    print(f"Processing CV file: {pdf_path}")
    
    try:
        # Import CV Sanitizer (would need to be packaged with Lambda)
        # For now, return mock data
        return generate_mock_result(original_filename)
    
    except ImportError as e:
        print(f"CV Sanitizer not available: {e}")
        # Fallback to mock processing
        return generate_mock_result(original_filename)

def generate_mock_result(original_filename):
    """Generate mock processing result for testing."""
    base_name = Path(original_filename).stem
    
    # Mock redacted data
    redacted_data = {
        'cv_filename': f"{base_name}_redacted.json",
        'original_filename': original_filename,
        'processing_date': datetime.now().isoformat(),
        'country_code': 'GB',
        'parser_used': 'mock',
        'pii_detected_count': 3,
        'user_edits_count': 0,
        'redacted_text': "John Doe <pii type=\"email\" serial=\"1\"> has experience in software engineering. " +
                        "Contact at <pii type=\"phone\" serial=\"2\">. Lives at <pii type=\"address\" serial=\"3\">.",
        'pii_summary': {
            'total': 3,
            'by_category': {
                'email': 1,
                'phone': 1,
                'address': 1
            },
            'confidence_distribution': {
                'high': 2,
                'medium': 1,
                'low': 0
            }
        },
        'audit_trail': {
            'user_edits': [],
            'processing_timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'environment': ENVIRONMENT
        }
    }
    
    # Mock PII mapping
    pii_mapping = {
        '<pii type="email" serial="1">': {
            'original': 'john.doe@example.com',
            'category': 'email',
            'position': {'start': 8, 'end': 26},
            'confidence': 0.9,
            'country_code': 'GB',
            'metadata': None
        },
        '<pii type="phone" serial="2">': {
            'original': '+44 7700 900123',
            'category': 'phone',
            'position': {'start': 58, 'end': 72},
            'confidence': 0.8,
            'country_code': 'GB',
            'metadata': None
        },
        '<pii type="address" serial="3">': {
            'original': '123 London Street, London, UK',
            'category': 'address',
            'position': {'start': 85, 'end': 110},
            'confidence': 0.7,
            'country_code': 'GB',
            'metadata': None
        }
    }
    
    return {
        'redacted_data': redacted_data,
        'pii_mapping': pii_mapping
    }

def create_deployment_package():
    """
    Create a deployment package for AWS Lambda.
    
    This function would be used during deployment to create a ZIP file
    containing the Lambda function and all dependencies.
    """
    # This would be called during deployment, not in the Lambda itself
    pass
