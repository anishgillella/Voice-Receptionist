"""
Form Mapper
Maps data from various sources to PDF form fields using semantic matching
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class FieldMapping:
    """Represents a mapping between a data source and a PDF form field"""
    pdf_field_name: str
    data_source_key: str
    transformer: Optional[callable] = None
    required: bool = False


class FormMapper:
    """Maps data to PDF form fields"""

    def __init__(self):
        """Initialize the form mapper"""
        self.mappings: List[FieldMapping] = []
        self.default_mappings = self._get_default_mappings()

    def _get_default_mappings(self) -> Dict[str, str]:
        """
        Common field name mappings
        Maps common PDF field patterns to data keys
        """
        return {
            # Personal Information
            "first_name": ["firstName", "first_name", "fname"],
            "last_name": ["lastName", "last_name", "lname"],
            "full_name": ["fullName", "full_name", "name"],
            "email": ["email", "email_address", "mail"],
            "phone": ["phone", "phone_number", "telephone"],
            "date_of_birth": ["dob", "date_of_birth", "birthDate"],
            
            # Address
            "address": ["address", "street_address", "street"],
            "city": ["city"],
            "state": ["state", "province"],
            "zip": ["zip", "postal_code", "zipcode"],
            "country": ["country"],
            
            # Company
            "company": ["company", "company_name", "organization"],
            "position": ["position", "job_title", "title"],
            "department": ["department"],
            
            # Date fields
            "date": ["date", "submission_date"],
            "signature_date": ["signature_date", "signDate"],
        }

    def add_mapping(self, pdf_field: str, data_key: str, 
                   transformer: Optional[callable] = None,
                   required: bool = False) -> None:
        """
        Add a manual mapping between PDF field and data key
        
        Args:
            pdf_field: Name of the PDF form field
            data_key: Key in the data dictionary
            transformer: Optional function to transform the value
            required: Whether this field is required
        """
        mapping = FieldMapping(
            pdf_field_name=pdf_field,
            data_source_key=data_key,
            transformer=transformer,
            required=required
        )
        self.mappings.append(mapping)

    def auto_map(self, pdf_fields: List[str], data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically map PDF fields to data using pattern matching
        
        Args:
            pdf_fields: List of PDF field names
            data_dict: Dictionary of data to map from
            
        Returns:
            Dictionary of field_name -> value mappings
        """
        result = {}
        
        for pdf_field in pdf_fields:
            # Normalize field name
            normalized_field = pdf_field.lower().replace(" ", "_")
            
            # Try to find matching data key
            for data_key, value in data_dict.items():
                if self._fields_match(normalized_field, data_key):
                    result[pdf_field] = value
                    break
        
        return result

    def map_data(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map data using defined mappings
        
        Args:
            data_dict: Source data dictionary
            
        Returns:
            Dictionary ready for PDF filling (pdf_field -> value)
        """
        result = {}
        
        for mapping in self.mappings:
            if mapping.data_source_key in data_dict:
                value = data_dict[mapping.data_source_key]
                
                # Apply transformer if provided
                if mapping.transformer:
                    value = mapping.transformer(value)
                
                result[mapping.pdf_field_name] = value
            elif mapping.required:
                raise ValueError(f"Required field '{mapping.data_source_key}' not found in data")
        
        return result

    def _fields_match(self, pdf_field: str, data_key: str) -> bool:
        """
        Check if PDF field and data key are likely the same
        
        Args:
            pdf_field: Normalized PDF field name
            data_key: Data dictionary key
            
        Returns:
            True if they likely match
        """
        normalized_key = data_key.lower().replace(" ", "_")
        
        # Exact match
        if pdf_field == normalized_key:
            return True
        
        # Check if one contains the other
        if pdf_field in normalized_key or normalized_key in pdf_field:
            return True
        
        # Check default mappings
        for pattern_key, patterns in self.default_mappings.items():
            if (pdf_field == pattern_key.lower() or 
                any(pattern in pdf_field for pattern in patterns)):
                if (normalized_key == pattern_key.lower() or 
                    any(pattern == normalized_key for pattern in patterns)):
                    return True
        
        return False


class DataTransformers:
    """Common data transformation functions"""

    @staticmethod
    def format_phone(phone: str) -> str:
        """Format phone number"""
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return phone

    @staticmethod
    def format_date(date_str: str, output_format: str = "%m/%d/%Y") -> str:
        """Format date string"""
        from datetime import datetime
        try:
            # Try common date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y%m%d"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime(output_format)
                except ValueError:
                    continue
            return date_str
        except Exception:
            return date_str

    @staticmethod
    def uppercase(text: str) -> str:
        """Convert to uppercase"""
        return str(text).upper()

    @staticmethod
    def capitalize_words(text: str) -> str:
        """Capitalize each word"""
        return str(text).title()
