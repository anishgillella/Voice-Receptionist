"""
Complete PDF Form Solution
Combines extraction + Joyfill API integration
"""

import json
from pathlib import Path
from pdf_filler import PDFFormFiller
from form_mapper import FormMapper


class CompletePDFSolution:
    """Complete solution: extract forms and prepare for Joyfill API"""
    
    def __init__(self, pdf_path: str):
        """Initialize complete solution"""
        self.pdf_path = pdf_path
        self.filler = PDFFormFiller(pdf_path)
        self.mapper = FormMapper()
        self.extracted_data = {}

    def extract_and_prepare(self, source_data: dict) -> dict:
        """
        Extract PDF form structure and prepare data for filling
        
        Args:
            source_data: Data to fill (from email/voice/etc)
            
        Returns:
            Dictionary with extracted fields and values
        """
        print("=" * 80)
        print("PDF FORM EXTRACTION & PREPARATION")
        print("=" * 80)
        
        # List all available fields
        fields = self.filler.list_fields()
        print(f"\n✓ Found {len(fields)} form fields in PDF")
        
        # Map source data to PDF fields
        print(f"\n📝 Mapping {len(source_data)} data points to PDF fields...")
        mapped_data = self.mapper.auto_map(list(fields.keys()), source_data)
        
        # Store extracted data
        self.extracted_data = mapped_data
        
        # Show results
        print(f"\n✓ Successfully mapped {len(mapped_data)} fields:\n")
        for field_name, value in mapped_data.items():
            print(f"  {field_name}: {value}")
        
        return mapped_data

    def save_for_joyfill(self, output_file: str) -> str:
        """
        Save extracted data in format ready for Joyfill API
        
        Args:
            output_file: Where to save the data file
            
        Returns:
            Path to saved file
        """
        # Create JoyDoc format
        joydoc = {
            "name": "Extracted Form Data",
            "fields": [
                {
                    "_id": field_name,
                    "type": "text",
                    "title": field_name,
                    "value": value
                }
                for field_name, value in self.extracted_data.items()
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(joydoc, f, indent=2)
        
        print(f"\n✅ JoyDoc format saved: {output_file}")
        print(f"   Ready to send to Joyfill API!")
        
        return output_file

    def save_as_json(self, output_file: str) -> str:
        """Save extracted data as simple JSON"""
        with open(output_file, 'w') as f:
            json.dump(self.extracted_data, f, indent=2)
        
        print(f"✅ JSON saved: {output_file}")
        return output_file

    def close(self):
        """Clean up"""
        self.filler.close()


# Example usage
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("COMPLETE PDF FORM SOLUTION")
    print("=" * 80)
    
    # Source data (could come from email, voice call, etc.)
    source_data = {
        "name": "Alexandra Richardson",
        "street": "42 Maple Street",
        "apartment": "Apt 3B",
        "postal_code": "SW1A 1AA",
        "city": "London",
        "country": "Britain",
        "gender": "Woman",
    }
    
    # Process
    solution = CompletePDFSolution("OoPdfFormExample.pdf")
    
    # Extract and map
    extracted = solution.extract_and_prepare(source_data)
    
    # Save in multiple formats
    solution.save_as_json("extracted_form_data.json")
    solution.save_for_joyfill("extracted_form_data_joydoc.json")
    
    print("\n" + "=" * 80)
    print("✅ EXTRACTION COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. extracted_form_data.json - Simple JSON with form data")
    print("2. extracted_form_data_joydoc.json - Joyfill API ready format")
    print("\nTo fill PDF:")
    print("  → Send to Joyfill API with your credentials")
    print("  → Or use any other PDF API service")
    print("=" * 80)
    
    solution.close()
