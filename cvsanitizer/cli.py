"""
Interactive CLI for CV Sanitizer

Provides a command-line interface for users to review and confirm PII detections
before proceeding with redaction.
"""

import sys
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich.text import Text
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    click = None

from .sanitizer import CVSanitizer
from .pii_detector import PIICategory


class CLIDisplay:
    """Handles CLI display with fallback for when rich is not available."""
    
    def __init__(self):
        self.use_rich = RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()
    
    def print_header(self, title: str):
        """Print a header."""
        if self.use_rich:
            self.console.print(Panel(title, title="CV Sanitizer"))
        else:
            print(f"\n{'='*60}")
            print(f"  {title}")
            print(f"{'='*60}")
    
    def print_table(self, headers: List[str], rows: List[List[str]], title: str = ""):
        """Print a table."""
        if self.use_rich:
            table = Table(title=title)
            for header in headers:
                table.add_column(header)
            
            for row in rows:
                table.add_row(*row)
            
            self.console.print(table)
        else:
            if title:
                print(f"\n{title}:")
                print("-" * len(title))
            
            # Calculate column widths
            col_widths = [len(header) for header in headers]
            for row in rows:
                for i, cell in enumerate(row):
                    if i < len(col_widths):
                        col_widths[i] = max(col_widths[i], len(str(cell)))
            
            # Print header
            header_row = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
            print(header_row)
            print("-" * len(header_row))
            
            # Print rows
            for row in rows:
                row_str = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
                print(row_str)
    
    def print_text(self, text: str, title: str = ""):
        """Print text with optional title."""
        if self.use_rich:
            if title:
                self.console.print(Panel(text, title=title))
            else:
                self.console.print(text)
        else:
            if title:
                print(f"\n{title}:")
                print("-" * len(title))
            print(text)
    
    def confirm(self, message: str, default: bool = False) -> bool:
        """Get user confirmation."""
        if self.use_rich:
            return Confirm.ask(message, default=default)
        else:
            response = input(f"{message} (y/N): ").lower().strip()
            return response in ['y', 'yes']
    
    def prompt(self, message: str, default: str = "") -> str:
        """Get user input."""
        if self.use_rich:
            return Prompt.ask(message, default=default)
        else:
            return input(f"{message} [{default}]: ").strip() or default
    
    def print_error(self, message: str):
        """Print error message."""
        if self.use_rich:
            self.console.print(f"[red]Error: {message}[/red]")
        else:
            print(f"Error: {message}", file=sys.stderr)
    
    def print_success(self, message: str):
        """Print success message."""
        if self.use_rich:
            self.console.print(f"[green]✓ {message}[/green]")
        else:
            print(f"✓ {message}")


class InteractiveCLI:
    """Interactive CLI for CV Sanitizer."""
    
    def __init__(self, country: str = "GB", pdf_library: str = "auto"):
        """Initialize CLI."""
        self.display = CLIDisplay()
        self.sanitizer = CVSanitizer(country=country, pdf_library=pdf_library)
        self.current_pdf = None
    
    def run(self, pdf_path: str, output_dir: Optional[str] = None, auto_confirm: bool = False):
        """
        Run the interactive CLI.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory for results
            auto_confirm: Skip interactive confirmation
        """
        try:
            # Load PDF
            self.display.print_header("CV Sanitizer - PII Detection and Redaction")
            self.display.print_success(f"Loading PDF: {pdf_path}")
            
            parse_result = self.sanitizer.load_pdf(pdf_path)
            self.display.print_success(
                f"Loaded {parse_result['page_count']} pages, "
                f"extracted {len(parse_result['text'])} characters"
            )
            
            # Detect PII
            self.display.print_success("Detecting PII...")
            detections = self.sanitizer.detect_pii()
            
            if not detections:
                self.display.print_text("No PII detected in the document.")
                if not self.display.confirm("Continue with processing anyway?"):
                    return
            
            # Show preview
            self.show_pii_preview()
            
            if not auto_confirm:
                # Interactive review
                self.interactive_review()
            
            # Generate redaction
            self.display.print_success("Generating redacted content...")
            redacted_text, pii_mapping = self.sanitizer.generate_redaction()
            
            # Show redaction summary
            self.show_redaction_summary(redacted_text, pii_mapping)
            
            # Confirm final processing
            if auto_confirm or self.display.confirm("Proceed with saving redacted files?"):
                # Save outputs
                output_files = self.sanitizer.save_outputs(output_dir)
                
                self.display.print_header("Processing Complete")
                self.display.print_success("Files saved successfully:")
                for file_type, path in output_files.items():
                    self.display.print_text(f"  {file_type}: {path}")
                
                # Show final summary
                self.show_final_summary()
            
            else:
                self.display.print_text("Processing cancelled by user.")
        
        except Exception as e:
            self.display.print_error(f"Processing failed: {e}")
            sys.exit(1)
    
    def show_pii_preview(self):
        """Show preview of detected PII."""
        preview = self.sanitizer.get_pii_preview()
        
        self.display.print_header("PII Detection Preview")
        
        # Summary table
        summary_rows = []
        for category, items in preview['by_category'].items():
            summary_rows.append([category, str(len(items))])
        
        if summary_rows:
            self.display.print_table(
                ["PII Type", "Count"],
                summary_rows,
                "Detected PII Summary"
            )
        
        # Show highlighted text (first 1000 chars)
        highlighted = preview['text_with_highlights']
        if len(highlighted) > 1000:
            highlighted = highlighted[:1000] + "..."
        
        self.display.print_text(highlighted, "Text with PII Highlighted")
    
    def interactive_review(self):
        """Interactive review and editing of PII detections."""
        while True:
            self.display.print_header("Interactive PII Review")
            
            # Show current detections
            detections = self.sanitizer.detected_pii
            
            if not detections:
                self.display.print_text("No PII items to review.")
                break
            
            # Show numbered list
            for i, match in enumerate(detections):
                confidence_pct = int(match.confidence * 100)
                country_info = f" ({match.country_code})" if match.country_code else ""
                self.display.print_text(
                    f"{i}: [{match.category.value}] {match.text} "
                    f"(confidence: {confidence_pct}%){country_info}"
                )
            
            # Show options
            self.display.print_text("\nOptions:")
            self.display.print_text("  <number> - Edit/remove specific PII item")
            self.display.print_text("  a - Add manual PII detection")
            self.display.print_text("  s - Show highlighted text")
            self.display.print_text("  d - Done with review")
            
            choice = self.display.prompt("Choose option", "").lower().strip()
            
            if choice == 'd':
                break
            elif choice == 'a':
                self.add_manual_pii()
            elif choice == 's':
                self.show_highlighted_text()
            elif choice.isdigit():
                try:
                    item_num = int(choice)
                    if 0 <= item_num < len(detections):
                        self.edit_pii_item(item_num)
                    else:
                        self.display.print_error("Invalid item number")
                except ValueError:
                    self.display.print_error("Invalid input")
            else:
                self.display.print_error("Invalid option")
    
    def edit_pii_item(self, item_num: int):
        """Edit a specific PII item."""
        match = self.sanitizer.detected_pii[item_num]
        
        self.display.print_header(f"Edit PII Item #{item_num}")
        self.display.print_text(f"Current: [{match.category.value}] {match.text}")
        
        # Show options
        self.display.print_text("\nOptions:")
        self.display.print_text("  k - Keep this PII item")
        self.display.print_text("  r - Remove this PII item")
        self.display.print_text("  e - Edit the PII text")
        
        choice = self.display.prompt("Choose option", "").lower().strip()
        
        if choice == 'k':
            # Keep - no action needed
            self.display.print_success("PII item kept")
        elif choice == 'r':
            # Remove
            updates = [{'id': item_num, 'action': 'remove'}]
            self.sanitizer.update_detections(updates)
            self.display.print_success("PII item removed")
        elif choice == 'e':
            # Edit
            new_text = self.display.prompt("Enter new PII text", match.text)
            if new_text and new_text != match.text:
                updates = [{'id': item_num, 'action': 'edit', 'new_text': new_text}]
                self.sanitizer.update_detections(updates)
                self.display.print_success(f"PII item updated to: {new_text}")
        else:
            self.display.print_error("Invalid option")
    
    def add_manual_pii(self):
        """Add a manual PII detection."""
        self.display.print_header("Add Manual PII Detection")
        
        # Get category
        categories = [cat.value for cat in PIICategory]
        self.display.print_text("Available categories:")
        for i, cat in enumerate(categories):
            self.display.print_text(f"  {i}: {cat}")
        
        try:
            cat_choice = int(self.display.prompt("Choose category", "0"))
            if 0 <= cat_choice < len(categories):
                category = categories[cat_choice]
            else:
                self.display.print_error("Invalid category")
                return
        except ValueError:
            self.display.print_error("Invalid input")
            return
        
        # Get text
        text = self.display.prompt("Enter PII text")
        if not text:
            self.display.print_error("PII text cannot be empty")
            return
        
        # Get position (optional)
        try:
            start_pos = int(self.display.prompt("Start position (optional)", "0") or "0")
            end_pos = start_pos + len(text)
        except ValueError:
            start_pos = 0
            end_pos = len(text)
        
        # Add the detection
        match = self.sanitizer.add_manual_detection(category, text, start_pos, end_pos)
        self.display.print_success(f"Added PII detection: [{category}] {text}")
    
    def show_highlighted_text(self):
        """Show text with PII highlighted."""
        preview = self.sanitizer.get_pii_preview()
        highlighted = preview['text_with_highlights']
        
        self.display.print_header("Highlighted Text")
        
        # Show in chunks if too long
        chunk_size = 2000
        for i in range(0, len(highlighted), chunk_size):
            chunk = highlighted[i:i+chunk_size]
            if i + chunk_size < len(highlighted):
                chunk += "..."
            self.display.print_text(chunk)
            
            if i + chunk_size < len(highlighted):
                input("Press Enter to continue...")
    
    def show_redaction_summary(self, redacted_text: str, pii_mapping: Dict[str, str]):
        """Show summary of redaction results."""
        self.display.print_header("Redaction Summary")
        
        # Show statistics
        self.display.print_text(f"Total PII items redacted: {len(pii_mapping)}")
        
        # Show by category
        by_category = {}
        for placeholder, info in pii_mapping.items():
            category = info['category']
            if category not in by_category:
                by_category[category] = 0
            by_category[category] += 1
        
        if by_category:
            rows = [[cat, str(count)] for cat, count in by_category.items()]
            self.display.print_table(["PII Type", "Count"], rows, "Redaction by Category")
        
        # Show sample of redacted text
        sample_length = min(500, len(redacted_text))
        sample = redacted_text[:sample_length]
        if len(redacted_text) > sample_length:
            sample += "..."
        
        self.display.print_text(sample, "Sample of Redacted Text")
    
    def show_final_summary(self):
        """Show final processing summary."""
        summary = self.sanitizer.get_processing_summary()
        
        self.display.print_header("Final Summary")
        
        rows = [
            ["PDF File", str(summary['pdf_path'])],
            ["Text Length", f"{summary['text_length']} characters"],
            ["PII Detected", str(summary['pii_detected_count'])],
            ["User Edits", str(summary['user_edits_count'])],
            ["Country Code", summary['country_code']],
        ]
        
        self.display.print_table(["Property", "Value"], rows)


@click.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--output-dir', '-o', type=click.Path(), help='Output directory for results')
@click.option('--country', '-c', default='GB', help='Country code for PII detection')
@click.option('--pdf-library', '-l', default='auto', help='PDF parsing library (auto/pymupdf/pdfplumber/pypdf2)')
@click.option('--auto-confirm', '-y', is_flag=True, help='Skip interactive confirmation')
def main(pdf_path: str, output_dir: str, country: str, pdf_library: str, auto_confirm: bool):
    """
    CV Sanitizer - Remove PII from CVs before sending to LLMs.
    
    This tool detects and redacts personally identifiable information from CVs
    using rule-based patterns (no AI required).
    
    Example:
        cvsanitizer my_cv.pdf --output-dir ./output --country GB
    """
    if not RICH_AVAILABLE:
        print("Warning: Rich library not available. CLI will use basic output.")
        print("Install with: pip install rich click")
    
    cli = InteractiveCLI(country=country, pdf_library=pdf_library)
    cli.run(pdf_path, output_dir, auto_confirm)


if __name__ == '__main__':
    main()
