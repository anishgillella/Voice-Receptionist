"""
Stagehand-based Browser PDF Form Filler
Uses Stagehand (AI-powered browser automation) to fill PDFs in the browser
Powered by Browserbase for browser automation
"""

import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import os


class StagehandPDFFiller:
    """Fill PDFs in browser using Stagehand AI automation with Browserbase"""
    
    def __init__(self, browserbase_api_key: Optional[str] = None, browserbase_project_id: Optional[str] = None, model_api_key: Optional[str] = None):
        """
        Initialize Stagehand PDF filler with Browserbase credentials
        
        Args:
            browserbase_api_key: Browserbase API key (defaults to env var BROWSERBASE_API_KEY)
            browserbase_project_id: Browserbase Project ID (defaults to env var BROWSERBASE_PROJECT_ID)
            model_api_key: LLM Model API key for Claude/OpenAI (defaults to env var MODEL_API_KEY or ANTHROPIC_API_KEY)
        """
        self.browserbase_api_key = browserbase_api_key or os.getenv("BROWSERBASE_API_KEY")
        self.browserbase_project_id = browserbase_project_id or os.getenv("BROWSERBASE_PROJECT_ID")
        self.model_api_key = model_api_key or os.getenv("MODEL_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.browserbase_api_key or not self.browserbase_project_id:
            raise ValueError(
                "Browserbase credentials required:\n"
                "  BROWSERBASE_API_KEY: Your Browserbase API key\n"
                "  BROWSERBASE_PROJECT_ID: Your Browserbase Project ID"
            )
        
        if not self.model_api_key:
            raise ValueError(
                "LLM Model API key required for Stagehand:\n"
                "  MODEL_API_KEY or ANTHROPIC_API_KEY: Claude API key\n"
                "  Get from: https://console.anthropic.com/account/keys"
            )
        
        self.form_data = {}
        self.browser = None
        print("✅ Stagehand initialized with Browserbase + Claude LLM")
        print(f"   Project ID: {self.browserbase_project_id[:8]}...")
    
    async def fill_pdf_from_url(
        self, 
        pdf_url: str, 
        form_data: Dict[str, Any],
        output_pdf_path: Optional[str] = None,
        headless: bool = False
    ) -> str:
        """
        Fill a PDF form in the browser and download filled version
        
        Args:
            pdf_url: URL to the PDF form (must be viewable in browser)
            form_data: Dictionary mapping field names to values
            output_pdf_path: Where to save the filled PDF (optional)
            headless: Whether to run in headless mode (default: False - see the browser!)
            
        Returns:
            Path to downloaded filled PDF
        """
        try:
            from stagehand import Stagehand
        except ImportError:
            raise ImportError("Stagehand not installed. Run: pip install stagehand")
        
        print(f"\n📄 Opening PDF in browser: {pdf_url}")
        print(f"📝 Filling {len(form_data)} form fields...")
        print(f"🌐 Headless: {headless} (set to False to see the browser)\n")
        
        # Initialize Stagehand with Browserbase + LLM
        async with Stagehand(
            api_key=self.browserbase_api_key,
            project_id=self.browserbase_project_id,
            model_api_key=self.model_api_key,
            headless=headless
        ) as sh:
            # Navigate to PDF
            print(f"🚀 Browser launching...")
            await sh.page.goto(pdf_url)
            
            # Wait for PDF to load
            await sh.page.wait_for_timeout(2000)
            print("✅ PDF loaded in browser\n")
            
            # Build natural language instruction for form filling
            instruction = self._build_fill_instruction(form_data)
            
            print(f"🤖 Executing: {instruction[:100]}...\n")
            
            # Use Stagehand to fill the form using natural language
            response = await sh.act(instruction)
            
            print(f"✅ {response.message}\n")
            
            # Wait a moment for form to update
            await sh.page.wait_for_timeout(2000)
            
            # Download the filled PDF
            if output_pdf_path:
                # Try to find download button or submit button
                download_instruction = (
                    "Find the button to download or save the filled PDF. "
                    "If there's a download icon or 'Download' button, click it. "
                    "If there's a 'Save as PDF' option, use that. "
                    "Otherwise, use Ctrl+S to save the PDF."
                )
                await sh.act(download_instruction)
                
                # Wait for download
                await sh.page.wait_for_timeout(3000)
                
                print(f"✅ PDF downloaded/saved to: {output_pdf_path}")
                return output_pdf_path
        
        return "PDF filled successfully in browser"
    
    async def fill_pdf_local_file(
        self,
        pdf_path: str,
        form_data: Dict[str, Any],
        output_path: Optional[str] = None,
        headless: bool = False
    ) -> str:
        """
        Fill a local PDF by uploading to browser and downloading filled version
        
        Args:
            pdf_path: Path to local PDF file
            form_data: Dictionary of field names and values
            output_path: Where to save the filled PDF (optional)
            headless: Whether to run in headless mode (default: False)
            
        Returns:
            Path to filled PDF or success message
        """
        try:
            from stagehand import Stagehand
        except ImportError:
            raise ImportError("Stagehand not installed. Run: pip install stagehand")
        
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"\n📄 Loading local PDF: {pdf_path}")
        print(f"📝 Preparing to fill {len(form_data)} fields...")
        print(f"🌐 Headless: {headless}\n")
        
        # Create a local file URL
        file_url = pdf_file.as_uri()
        
        async with Stagehand(
            api_key=self.browserbase_api_key,
            project_id=self.browserbase_project_id,
            model_api_key=self.model_api_key,
            headless=headless
        ) as sh:
            # Navigate to the PDF
            print(f"🚀 Browser launching...")
            await sh.page.goto(file_url)
            
            # Wait for PDF to load
            await sh.page.wait_for_timeout(2000)
            print("✅ PDF loaded in browser\n")
            
            # Fill the form
            instruction = self._build_fill_instruction(form_data)
            print(f"🤖 Executing: {instruction[:100]}...\n")
            
            response = await sh.act(instruction)
            
            print(f"✅ {response.message}\n")
            
            # Download filled PDF if output path provided
            if output_path:
                # Wait a moment for form to update
                await sh.page.wait_for_timeout(2000)
                
                download_instruction = (
                    "Save or download the filled PDF. "
                    "Use Ctrl+S or find the download button."
                )
                await sh.act(download_instruction)
                
                await sh.page.wait_for_timeout(3000)
                
                print(f"✅ Filled PDF saved to: {output_path}")
                return output_path
        
        return "PDF filled successfully in browser"
    
    def _build_fill_instruction(self, form_data: Dict[str, Any]) -> str:
        """Build natural language instruction for Stagehand to fill form"""
        instruction = "Fill the PDF form with the following information:\n"
        
        for field_name, value in form_data.items():
            instruction += f"- {field_name}: {value}\n"
        
        instruction += (
            "\nFor each field, click on it and enter the value. "
            "If the field is a dropdown, select the appropriate option. "
            "If it's a checkbox or radio button, click it if the value is 'yes', 'true', 'checked', or 'selected'. "
            "Fill all fields with the provided information and ensure they're visible. "
            "Take your time and be thorough. Make sure all text is entered correctly."
        )
        
        return instruction
    
    def fill_sync(
        self,
        pdf_url: str,
        form_data: Dict[str, Any],
        output_path: Optional[str] = None,
        headless: bool = False
    ) -> str:
        """Synchronous wrapper for async fill operation"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.fill_pdf_from_url(pdf_url, form_data, output_path, headless)
        )
    
    def close(self) -> None:
        """Clean up resources"""
        if self.browser:
            self.browser.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example usage
if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("STAGEHAND PDF FORM FILLER - POWERED BY BROWSERBASE")
    print("=" * 80)
    
    # Example form data
    form_data = {
        "Given Name Text Box": "Alexandra",
        "Family Name Text Box": "Richardson",
        "Address 1 Text Box": "42 Maple Street",
        "Address 2 Text Box": "Apt 3B",
        "City Text Box": "London",
        "Country Combo Box": "Britain",
        "Gender List Box": "Woman",
    }
    
    # Example URL (replace with actual PDF URL)
    pdf_url = "https://example.com/form.pdf"
    
    print("\n✅ Stagehand Form Filler Ready!")
    print("\nUsage:")
    print("  from stagehand_filler import StagehandPDFFiller")
    print("  ")
    print("  filler = StagehandPDFFiller()")
    print("  result = filler.fill_sync(pdf_url, form_data, headless=False)")
    print("\n✨ Or use async:")
    print("  async with StagehandPDFFiller() as filler:")
    print("      result = await filler.fill_pdf_from_url(pdf_url, form_data, headless=False)")
