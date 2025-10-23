# Local Forms - PDF Form Filler

This module provides programmatic PDF form filling using **PyMuPDF (fitz)**, which is more powerful and reliable than PyPDF for this purpose.

## Why PyMuPDF?

- ✅ Better form field detection and manipulation
- ✅ Handles complex PDFs well
- ✅ Better performance
- ✅ More active development
- ✅ Supports both AcroForms and XFA forms

## Installation

```bash
pip install PyMuPDF
```

## Quick Start

### Basic Example: Fill PDF with Direct Data

```python
from local_forms.pdf_filler import PDFFormFiller

# Open and fill PDF
with PDFFormFiller("form.pdf") as filler:
    # List available fields
    print(filler.list_fields())
    
    # Fill fields
    filler.fill_fields({
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com"
    })
    
    # Save
    filler.save("form_filled.pdf")
```

### Smart Mapping: Use FormMapper

```python
from local_forms.pdf_filler import PDFFormFiller
from local_forms.form_mapper import FormMapper, DataTransformers

# Initialize mapper
mapper = FormMapper()

# Add custom mappings with transformers
mapper.add_mapping(
    pdf_field="Phone",
    data_key="phone_number",
    transformer=DataTransformers.format_phone
)

# Source data (from database, API, email, etc.)
source_data = {
    "firstName": "Jane",
    "phone_number": "5551234567"
}

# Map and fill
pdf_data = mapper.map_data(source_data)

with PDFFormFiller("form.pdf") as filler:
    filler.fill_fields(pdf_data)
    filler.save("form_filled.pdf")
```

### Auto-Mapping: Automatic Field Discovery

```python
from local_forms.form_mapper import FormMapper

# Auto-detect and map fields
mapper = FormMapper()
auto_mapped = mapper.auto_map(
    pdf_fields=["first_name", "last_name"],
    data_dict={"firstName": "Bob", "lastName": "Smith"}
)

# auto_mapped = {"first_name": "Bob", "last_name": "Smith"}
```

## API Reference

### PDFFormFiller

**Initialize:**
```python
filler = PDFFormFiller("path/to/form.pdf")
```

**Methods:**
- `list_fields()` - Get all form fields with metadata
- `fill_field(field_name, value)` - Fill a single field
- `fill_fields(fields_dict)` - Fill multiple fields
- `save(output_path)` - Save filled PDF
- `save_json(output_path)` - Export form data as JSON
- `close()` - Close the PDF document

**Context Manager:**
```python
with PDFFormFiller("form.pdf") as filler:
    filler.fill_fields({"name": "John"})
    filler.save("filled.pdf")
```

### FormMapper

**Methods:**
- `add_mapping(pdf_field, data_key, transformer, required)` - Add custom mapping
- `auto_map(pdf_fields, data_dict)` - Auto-detect field mappings
- `map_data(data_dict)` - Map source data using defined mappings

### DataTransformers

**Available Transformers:**
- `format_phone(phone)` - Format phone to (XXX) XXX-XXXX
- `format_date(date_str, output_format)` - Convert date formats
- `uppercase(text)` - Convert to uppercase
- `capitalize_words(text)` - Capitalize each word

## Use Cases

### 1. Email-Driven Form Filling
Extract information from emails and auto-fill forms:

```python
# Extract data from email
email_data = {
    "sender_name": "John Smith",
    "sender_email": "john@example.com"
}

# Map and fill form
mapper = FormMapper()
mapper.add_mapping("Full Name", "sender_name")
mapper.add_mapping("Email", "sender_email")

pdf_data = mapper.map_data(email_data)

with PDFFormFiller("form.pdf") as filler:
    filler.fill_fields(pdf_data)
    filler.save(f"form_{email_data['sender_name']}.pdf")
```

### 2. Database-Driven Bulk Filling
Fill multiple forms from database:

```python
from database import get_customer_data

customers = get_customer_data()

for customer in customers:
    with PDFFormFiller("template.pdf") as filler:
        filler.fill_fields(customer)
        filler.save(f"forms/{customer['id']}_filled.pdf")
```

### 3. Voice Call Context
Fill forms based on voice call data:

```python
# After voice call, extract relevant info
call_data = {
    "customer_name": "Alice Brown",
    "phone_number": "5559876543",
    "service_date": "2025-10-23"
}

mapper = FormMapper()
mapper.add_mapping("Name", "customer_name")
mapper.add_mapping("Phone", "phone_number", 
                  transformer=DataTransformers.format_phone)
mapper.add_mapping("Date", "service_date")

with PDFFormFiller("service_form.pdf") as filler:
    filler.fill_fields(mapper.map_data(call_data))
    filler.save("completed_service_form.pdf")
```

## Field Matching Rules

When using `auto_map()`, fields are matched based on:
1. **Exact name match** (case-insensitive)
2. **Substring matching** (field name contains data key or vice versa)
3. **Pattern library** - Common field name patterns (email, phone, name, etc.)

Example:
- PDF field "first_name" matches data key "firstName", "first_name", "fname"
- PDF field "email_address" matches data key "email", "email_address", "mail"

## Data Formats Supported

| Type | Formats |
|------|---------|
| Phone | `5551234567`, `555-123-4567`, `(555)123-4567` |
| Date | `2025-10-23`, `10/23/2025`, `23/10/2025`, `20251023` |
| Text | Any string |
| Number | Integers and floats |

## Error Handling

```python
try:
    with PDFFormFiller("form.pdf") as filler:
        results = filler.fill_fields(data)
        
        # Check which fields failed
        for field, success in results.items():
            if not success:
                print(f"Failed to fill: {field}")
                
        filler.save("filled.pdf")
except FileNotFoundError:
    print("PDF file not found")
except Exception as e:
    print(f"Error: {e}")
```

## Limitations

- PDFs must have embedded form fields (AcroForms)
- Non-interactive PDFs require image overlay approach (not yet implemented)
- Encrypted PDFs may require password
- Some advanced form features may not be supported

## Next Steps

- Integrate with email_agent to extract form data from emails
- Add support for non-interactive PDFs with image overlay
- Implement form field validation and constraints
- Add batch processing capabilities
