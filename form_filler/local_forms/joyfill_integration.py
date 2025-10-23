"""
Joyfill Integration - Fill PDFs using Joyfill API
Uses their public and secret keys to generate filled PDFs
"""

import json
import requests
from typing import Dict, Any, Optional
from pathlib import Path
import os


class JoyfillPDFFiller:
    """Fill PDFs using Joyfill API"""
    
    # Joyfill API endpoints
    BASE_URL = "https://api-joy.joyfill.io"
    
    def __init__(self, public_key: str, secret_key: str):
        """
        Initialize Joyfill filler with API credentials
        
        Args:
            public_key: Joyfill Public Key
            secret_key: Joyfill Secret Key
        """
        self.public_key = public_key
        self.secret_key = secret_key
        self.form_data = {}
        
        # Verify credentials
        if not self._verify_credentials():
            raise ValueError("Invalid Joyfill credentials")
        
        print("✅ Joyfill API authenticated successfully")

    def _verify_credentials(self) -> bool:
        """Verify Joyfill API credentials"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f"{self.BASE_URL}/documents",
                headers=headers,
                timeout=5
            )
            return response.status_code in [200, 401, 403, 404]
        except Exception as e:
            print(f"Warning: Could not verify credentials: {e}")
            return True

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Joyfill API"""
        import base64
        credentials = base64.b64encode(
            f"{self.public_key}:{self.secret_key}".encode()
        ).decode()
        
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }

    def fill_fields(self, data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Store fields to fill
        
        Args:
            data: Form data to fill
            
        Returns:
            Success status
        """
        results = {}
        for field_name, value in data.items():
            self.form_data[field_name] = str(value)
            results[field_name] = True
            print(f"✓ {field_name}: {value}")
        
        return results

    def fill_from_json(self, json_file: str) -> Dict[str, bool]:
        """
        Load form data from JSON and fill
        
        Args:
            json_file: Path to JSON file with form data
            
        Returns:
            Success status
        """
        with open(json_file) as f:
            data = json.load(f)
        
        return self.fill_fields(data)

    def create_document_and_fill(self, pdf_path: str, output_path: str) -> Optional[str]:
        """
        Create a Joyfill document and fill it with data
        
        Args:
            pdf_path: Path to source PDF
            output_path: Where to save filled PDF
            
        Returns:
            Path to filled PDF if successful
        """
        try:
            # Step 1: Upload PDF to Joyfill
            print(f"\n📤 Uploading PDF to Joyfill...")
            document_id = self._upload_pdf(pdf_path)
            print(f"✓ Document created with ID: {document_id}")
            
            # Step 2: Fill the document with data
            print(f"\n📝 Filling document with {len(self.form_data)} fields...")
            self._fill_document(document_id, self.form_data)
            print(f"✓ Document filled")
            
            # Step 3: Export filled PDF
            print(f"\n📥 Downloading filled PDF...")
            self._export_pdf(document_id, output_path)
            print(f"✅ Filled PDF saved: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def _upload_pdf(self, pdf_path: str) -> str:
        """
        Upload PDF to Joyfill
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Document ID
        """
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            headers = {
                "Authorization": self._get_headers()["Authorization"]
                # Don't set Content-Type for multipart - requests will set it
            }
            
            response = requests.post(
                f"{self.BASE_URL}/documents",
                headers=headers,
                files=files,
                timeout=30
            )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")
        
        data = response.json()
        doc_id = data.get('id') or data.get('document_id') or data.get('_id')
        if not doc_id:
            raise Exception(f"No document ID in response: {data}")
        return doc_id

    def _fill_document(self, document_id: str, data: Dict[str, Any]) -> None:
        """
        Fill document fields
        
        Args:
            document_id: Joyfill document ID
            data: Form data to fill
        """
        headers = self._get_headers()
        
        # Convert form data to Joyfill format
        fields = []
        for field_name, value in data.items():
            fields.append({
                "name": field_name,
                "value": str(value)
            })
        
        payload = {
            "fields": fields
        }
        
        response = requests.put(
            f"{self.BASE_URL}/document/{document_id}",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Fill failed: {response.status_code} - {response.text}")

    def _export_pdf(self, document_id: str, output_path: str) -> None:
        """
        Export filled PDF
        
        Args:
            document_id: Joyfill document ID
            output_path: Where to save PDF
        """
        headers = self._get_headers()
        
        response = requests.get(
            f"{self.BASE_URL}/document/{document_id}/pdf",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Export failed: {response.status_code}")
        
        with open(output_path, 'wb') as f:
            f.write(response.content)

    def save_json(self, output_path: str) -> None:
        """Save form data as JSON"""
        json_file = str(output_path).replace('.pdf', '_data.json')
        with open(json_file, 'w') as f:
            json.dump(self.form_data, f, indent=2)
        print(f"✓ Form data: {json_file}")

    def close(self) -> None:
        """Close connection"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Test example
if __name__ == "__main__":
    # Your credentials - use environment variables!
    PUBLIC_KEY = os.getenv("JOYFILL_PUBLIC_KEY")
    SECRET_KEY = os.getenv("JOYFILL_SECRET_KEY")
    
    if not PUBLIC_KEY or not SECRET_KEY:
        print("❌ Joyfill credentials not found in environment")
        print("   Set JOYFILL_PUBLIC_KEY and JOYFILL_SECRET_KEY environment variables")
        exit(1)
    
    print("=" * 80)
    print("JOYFILL PDF FILLER TEST")
    print("=" * 80)
    
    try:
        with JoyfillPDFFiller(PUBLIC_KEY, SECRET_KEY) as filler:
            print("\nFilling form...")
            filler.fill_fields({
                "Given Name Text Box": "Alexandra",
                "Family Name Text Box": "Richardson",
                "Address 1 Text Box": "42 Maple Street",
                "Address 2 Text Box": "Apt 3B",
                "Postcode Text Box": "SW1A 1AA",
                "City Text Box": "London",
                "Country Combo Box": "Britain",
                "Gender List Box": "Woman",
            })
            
            print("\nCreating filled PDF via Joyfill...")
            result = filler.create_document_and_fill(
                "OoPdfFormExample.pdf",
                "OoPdfFormExample_JOYFILL_FILLED.pdf"
            )
            
            if result:
                print(f"\n✅ SUCCESS! Filled PDF created: {result}")
            else:
                print("\n❌ Failed to create filled PDF")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
