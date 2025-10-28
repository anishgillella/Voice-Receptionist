"""
Example Usage of PDF Form Filler
Shows how to fill PDFs with local data
"""

from pdf_filler import PDFFormFiller, PDFFormExtractor
from form_mapper import FormMapper, DataTransformers


def example_basic_fill():
    """Basic example: Fill PDF with direct field mapping"""
    print("=" * 50)
    print("Example 1: Basic PDF Filling")
    print("=" * 50)
    
    # Open PDF
    with PDFFormFiller("sample_form.pdf") as filler:
        # List available fields
        print("Available fields:")
        for field_name, field_info in filler.list_fields().items():
            print(f"  - {field_name}: {field_info['type']}")
        
        # Fill fields
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "555-1234",
        }
        
        results = filler.fill_fields(data)
        print(f"\nFill results: {results}")
        
        # Save filled PDF
        filler.save("sample_form_filled.pdf")
        
        # Also save as JSON
        filler.save_json("form_data.json")


def example_with_mapping():
    """Example: Use form mapper for flexible mapping"""
    print("\n" + "=" * 50)
    print("Example 2: Smart Field Mapping")
    print("=" * 50)
    
    # Initialize mapper
    mapper = FormMapper()
    
    # Add custom mappings
    mapper.add_mapping(
        pdf_field="Phone",
        data_key="phone_number",
        transformer=DataTransformers.format_phone
    )
    mapper.add_mapping(
        pdf_field="DateOfBirth",
        data_key="dob",
        transformer=lambda x: DataTransformers.format_date(x, "%m/%d/%Y")
    )
    
    # Source data (could be from database, API, email, etc.)
    source_data = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com",
        "phone_number": "5551234567",
        "dob": "1990-05-15",
    }
    
    # Map data to PDF fields
    pdf_data = mapper.map_data(source_data)
    print(f"Mapped data: {pdf_data}")
    
    # Fill PDF with mapped data
    with PDFFormFiller("sample_form.pdf") as filler:
        filler.fill_fields(pdf_data)
        filler.save("sample_form_mapped_filled.pdf")


def example_auto_mapping():
    """Example: Automatic field discovery and mapping"""
    print("\n" + "=" * 50)
    print("Example 3: Automatic Mapping")
    print("=" * 50)
    
    with PDFFormFiller("sample_form.pdf") as filler:
        # Get PDF fields
        pdf_fields = list(filler.list_fields().keys())
        
        # Source data
        source_data = {
            "firstName": "Bob",
            "lastName": "Johnson",
            "email_address": "bob@example.com",
            "phone": "(555) 123-4567",
        }
        
        # Auto-map
        mapper = FormMapper()
        auto_mapped = mapper.auto_map(pdf_fields, source_data)
        print(f"Auto-mapped fields: {auto_mapped}")
        
        filler.fill_fields(auto_mapped)
        filler.save("sample_form_auto_filled.pdf")


def example_extract_data():
    """Example: Extract data from filled PDF"""
    print("\n" + "=" * 50)
    print("Example 4: Extract Form Data")
    print("=" * 50)
    
    # Extract data from filled PDF
    extracted_data = PDFFormExtractor.extract_form_data("sample_form_filled.pdf")
    print("Extracted data:")
    for field, value in extracted_data.items():
        print(f"  {field}: {value}")
    
    # Save as JSON
    PDFFormExtractor.extract_to_json(
        "sample_form_filled.pdf",
        "extracted_form_data.json"
    )


if __name__ == "__main__":
    # Run examples (make sure sample_form.pdf exists)
    try:
        example_basic_fill()
        example_with_mapping()
        example_auto_mapping()
        example_extract_data()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please make sure you have a 'sample_form.pdf' in the current directory")
