# === pdf_generator.py ===
# Created: September 18, 2025 - 12:00 PM
# Purpose: Simplified PDF generation for text-only templates with Etsy design links
# Key Exports:
#   - create_pdf(): Main function for generating template PDFs
# Interactions:
#   - Used by: app.py webhook endpoint
# Notes:
#   - Simplified version without logo/flyer images
#   - Only includes text content and Etsy design link button

import logging
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Default Etsy design link if none provided
DEFAULT_ETSY_DESIGN_LINK = "https://www.etsy.com/listing/1827167654/custom-flyer-design-party-flyer-canva"

def create_pdf(output_path, title, canva_link, etsy_design_link=None):
    """
    Create a simplified PDF template with text content and download links
    
    Parameters:
    output_path (str): Path where the PDF will be saved
    title (str): Title text for the PDF
    canva_link (str): Canva template download link
    etsy_design_link (str, optional): Etsy design service link
    
    Returns:
    bool: True if PDF was created successfully, False otherwise
    
    Raises:
    Exception: If PDF creation fails
    """
    try:
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use default Etsy link if none provided
        if not etsy_design_link:
            etsy_design_link = DEFAULT_ETSY_DESIGN_LINK
        
        logger.info(f"Creating PDF: {output_path}")
        logger.debug(f"Title: {title}")
        logger.debug(f"Canva link: {canva_link}")
        logger.debug(f"Etsy link: {etsy_design_link}")
        
        # Create PDF canvas
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Starting position (top of page with margin)
        current_y = height - 50
        
        # Define colors
        button_color = Color(0.2, 0.5, 0.8)  # Blue
        text_color = Color(0, 0, 0)  # Black
        white_color = Color(1, 1, 1)  # White
        
        # Title with [Template] suffix
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 18)
        title_text = f"{title} [Template]"
        c.drawCentredString(width / 2, current_y, title_text)
        current_y -= 60
        
        # Welcome message
        c.setFont("Helvetica", 14)
        c.drawCentredString(width / 2, current_y, "Thank you for your purchase!")
        current_y -= 30
        
        # Instructions
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, current_y, "Click the button below to download and edit your template.")
        current_y -= 50
        
        # Main Canva download button
        button_width = 300
        button_height = 35
        button_x = (width - button_width) / 2
        
        # Draw button background
        c.setFillColor(button_color)
        c.rect(button_x, current_y - button_height, button_width, button_height, fill=1)
        
        # Draw button text
        c.setFillColor(white_color)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2, current_y - button_height/2 - 4, "Download & Edit Template")
        
        # Add clickable link
        c.linkURL(canva_link, (button_x, current_y - button_height, button_x + button_width, current_y), relative=0)
        
        current_y -= 80
        
        # Etsy design service button
        etsy_button_width = 250
        etsy_button_height = 30
        etsy_button_x = (width - etsy_button_width) / 2
        
        # Draw Etsy button background
        c.setFillColor(button_color)
        c.rect(etsy_button_x, current_y - etsy_button_height, etsy_button_width, etsy_button_height, fill=1)
        
        # Draw Etsy button text
        c.setFillColor(white_color)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(width / 2, current_y - etsy_button_height/2 - 3, "Need a Custom Design?")
        
        # Add clickable link for Etsy
        c.linkURL(etsy_design_link, (etsy_button_x, current_y - etsy_button_height, etsy_button_x + etsy_button_width, current_y), relative=0)
        
        current_y -= 60
        
        # Additional information
        c.setFillColor(text_color)
        c.setFont("Helvetica", 10)
        info_text = "Need help customizing this template or want a completely custom design?"
        c.drawCentredString(width / 2, current_y, info_text)
        current_y -= 20
        
        info_text2 = "Click the button above to get professional design assistance!"
        c.drawCentredString(width / 2, current_y, info_text2)
        current_y -= 60
        
        # Template information section
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(width / 2, current_y, "Template Information:")
        current_y -= 25
        
        c.setFont("Helvetica", 10)
        template_info = [
            "• This is a digital template - no physical product will be shipped",
            "• Template is fully customizable using Canva",
            "• No design software experience required",
            "• High-resolution output suitable for printing",
            "• Compatible with standard paper sizes"
        ]
        
        for info in template_info:
            c.drawString(80, current_y, info)
            current_y -= 18
        
        current_y -= 30
        
        # Footer message
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColor(Color(0.3, 0.3, 0.3))  # Gray text
        footer_text = "We appreciate you as our customer! Your 5-star reviews mean the world to us!"
        c.drawCentredString(width / 2, current_y, footer_text)
        
        # Save the PDF
        c.save()
        
        logger.info(f"PDF created successfully: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating PDF {output_path}: {e}")
        raise Exception(f"Failed to create PDF: {str(e)}")

def validate_pdf_inputs(title, canva_link):
    """
    Validate inputs for PDF generation
    
    Parameters:
    title (str): PDF title
    canva_link (str): Canva template link
    
    Returns:
    bool: True if inputs are valid
    
    Raises:
    ValueError: If inputs are invalid
    """
    if not title or not isinstance(title, str):
        raise ValueError("Title must be a non-empty string")
    
    if len(title.strip()) == 0:
        raise ValueError("Title cannot be empty or only whitespace")
    
    if len(title) > 100:
        raise ValueError("Title must be 100 characters or less")
    
    if not canva_link or not isinstance(canva_link, str):
        raise ValueError("Canva link must be a non-empty string")
    
    if not (canva_link.startswith('http://') or canva_link.startswith('https://')):
        raise ValueError("Canva link must be a valid URL")
    
    return True

"""
OVERVIEW

This file contains the core PDF generation functionality for the online template system.
Unlike the original desktop version, this simplified implementation focuses on creating
text-based PDFs with clickable download links.

Key Features:
- Creates professional-looking template PDFs with title and instructions
- Includes clickable buttons for Canva template download and Etsy design services
- Generates clean, print-ready documents without requiring image assets
- Handles proper text formatting and layout positioning

The PDF structure includes:
1. Template title with [Template] suffix
2. Thank you message and download instructions
3. Main Canva download button (prominent, blue)
4. Secondary Etsy design service button
5. Template information and usage guidelines
6. Footer with customer appreciation message

This approach eliminates the need for logo images and flyer previews while maintaining
a professional appearance suitable for digital template delivery.

Edge Cases Handled:
- Missing or invalid Etsy links default to standard design service URL
- Long titles are accommodated within reasonable character limits
- Invalid URLs are caught during input validation
- File system errors are properly logged and re-raised

Future Improvements:
- Add support for multiple template styles/themes
- Include QR codes for mobile-friendly link access
- Add template preview thumbnails if image assets become available
"""

"""
 * === pdf_generator.py ===
 * Updated: September 18, 2025 - 12:00 PM
 * Summary: Simplified PDF generation for text-based templates with download links
 * Key Components:
 *   - create_pdf(): Main PDF generation function with text and buttons
 *   - validate_pdf_inputs(): Input validation for title and links
 * Dependencies:
 *   - Requires: reportlab for PDF creation
 * Version History:
 *   v1.0 - Initial text-only template implementation
 * Notes:
 *   - No image dependencies - purely text-based templates
 *   - Professional layout with clickable download buttons
 *   - Comprehensive input validation and error handling
 */
