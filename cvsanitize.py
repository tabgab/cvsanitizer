#!/usr/bin/env python3
"""
CV Sanitizer - Command Line Interface

Entry point for the CV Sanitizer CLI tool.
"""

import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cvsanitizer.cli import main

if __name__ == '__main__':
    main()
