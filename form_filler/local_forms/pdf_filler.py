"""
PDF Form Filler using PyMuPDF
Handles filling AcroForm fields in PDF documents
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import fitz  # PyMuPDF


class PDFFormFiller:
    """Fill PDF forms using PyMuPDF"""

    def __init__(self, pdf_path: str):
        """
        Initialize PDF form filler
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.doc = fitz.open(pdf_path)
        self.form_fields = None
        self._extract_form_fields()

    def _extract_form_fields(self) -> None:
        """Extract all form fields from the PDF"""
        self.form_fields = {}
        
        for page_num, page in enumerate(self.doc):
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    try:
                        # Get field name and other info
                        field_name = widget.field_name or f"field_{page_num}_{len(self.form_fields)}"
                        field_type = widget.field_type
                        field_value = widget.field_value
                        
                        self.form_fields[field_name] = {
                            "page": page_num,
                            "page_obj": page,
                            "type": field_type,
                            "value": field_value,
                            "rect": widget.rect,
                            "widget_ref": widget,
                        }
                    except Exception as e:
                        print(f"Warning: Could not extract field info: {str(e)}")
                        continue

    def list_fields(self) -> Dict[str, Dict[str, Any]]:
        """
        List all form fields in the PDF
        
        Returns:
            Dictionary with field names and their properties
        """
        # Return a clean version without widget_ref and page_obj
        return {
            name: {k: v for k, v in field.items() if k not in ["widget_ref", "page_obj"]}
            for name, field in self.form_fields.items()
        }

    def fill_field(self, field_name: str, value: Any) -> bool:
        """
        Fill a single form field
        
        Args:
            field_name: Name of the field to fill
            value: Value to fill in
            
        Returns:
            True if successful, False otherwise
        """
        if field_name not in self.form_fields:
            print(f"Field '{field_name}' not found. Available fields: {list(self.form_fields.keys())}")
            return False

        field_info = self.form_fields[field_name]
        widget = field_info["widget_ref"]
        
        try:
            # Set the field value directly on the widget
            widget.field_value = str(value)
            return True
        except Exception as e:
            print(f"Error filling field {field_name}: {str(e)}")
            return False

    def fill_fields(self, fields_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Fill multiple form fields at once
        
        Args:
            fields_data: Dictionary mapping field names to values
            
        Returns:
            Dictionary with success status for each field
        """
        results = {}
        for field_name, value in fields_data.items():
            results[field_name] = self.fill_field(field_name, value)
        
        return results

    def save(self, output_path: str) -> None:
        """
        Save the filled PDF to a new file
        
        Args:
            output_path: Path where to save the filled PDF
        """
        # If saving to a different location, save incrementally from original
        if str(output_path) != str(self.pdf_path):
            self.doc.save(output_path, incremental=False, garbage=4)
        else:
            self.doc.save(output_path)
        print(f"PDF saved to: {output_path}")

    def save_json(self, output_path: str) -> None:
        """
        Save filled form data as JSON
        
        Args:
            output_path: Path where to save the JSON
        """
        form_data = {}
        
        # Open the saved PDF to get the fresh data
        try:
            temp_doc = fitz.open(str(output_path))
            for page in temp_doc:
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        try:
                            field_name = widget.field_name
                            field_value = widget.field_value
                            if field_name:
                                form_data[field_name] = field_value
                        except Exception:
                            continue
            temp_doc.close()
        except Exception as e:
            print(f"Warning: Could not open saved PDF to extract data: {e}")
            # Fallback: use current document
            for page_num, page in enumerate(self.doc):
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        try:
                            field_name = widget.field_name
                            field_value = widget.field_value
                            if field_name:
                                form_data[field_name] = field_value
                        except Exception:
                            continue
        
        with open(output_path.replace('.pdf', '') + '_form.json', 'w') as f:
            json.dump(form_data, f, indent=2)
        
        print(f"Form data saved to: {output_path.replace('.pdf', '')}_form.json")

    def close(self) -> None:
        """Close the PDF document"""
        if self.doc:
            self.doc.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class PDFFormExtractor:
    """Extract data from filled PDFs"""

    @staticmethod
    def extract_form_data(pdf_path: str) -> Dict[str, Any]:
        """
        Extract form data from a filled PDF
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with field names and their values
        """
        doc = fitz.open(pdf_path)
        form_data = {}
        
        try:
            for page in doc:
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        try:
                            field_name = widget.field_name
                            field_value = widget.field_value
                            
                            if field_name:
                                form_data[field_name] = field_value
                        except Exception:
                            continue
        finally:
            doc.close()
        
        return form_data

    @staticmethod
    def extract_to_json(pdf_path: str, output_path: str) -> None:
        """
        Extract form data and save as JSON
        
        Args:
            pdf_path: Path to the PDF file
            output_path: Path to save JSON
        """
        form_data = PDFFormExtractor.extract_form_data(pdf_path)
        
        with open(output_path, 'w') as f:
            json.dump(form_data, f, indent=2)
        
        print(f"Form data extracted to: {output_path}")
