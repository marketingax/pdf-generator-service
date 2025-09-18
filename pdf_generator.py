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
import requests
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Default Etsy design link if none provided
DEFAULT_ETSY_DESIGN_LINK = "https://www.etsy.com/listing/1827167654/custom-flyer-design-party-flyer-canva"

def download_image(url, timeout=10):
    """
    Download image from URL and return as ImageReader object
    
    Parameters:
    url (str): Image URL to download
    timeout (int): Request timeout in seconds
    
    Returns:
    ImageReader: ReportLab ImageReader object or None if failed
    """
    try:
        if not url or not url.startswith(('http://', 'https://')):
            logger.warning(f"Invalid image URL: {url}")
            return None
            
        logger.info(f"Downloading image from: {url}")
        
        # Add headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, timeout=timeout, stream=True, headers=headers)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if not any(img_type in content_type for img_type in ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']):
            logger.warning(f"URL does not appear to be an image: {content_type}")
            return None
        
        # Create temporary file for the image
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive chunks
                    temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        # Verify the file was written and has content
        if Path(temp_file_path).stat().st_size == 0:
            logger.warning(f"Downloaded image file is empty: {url}")
            Path(temp_file_path).unlink()
            return None
        
        # Create ImageReader from the downloaded file
        image_reader = ImageReader(temp_file_path)
        
        logger.info(f"Successfully downloaded image: {url}")
        return image_reader
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error downloading image from {url}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to download image from {url}: {e}")
        return None

def draw_image(canvas, image_reader, x, y, width):
    """
    Draw an image on the PDF canvas
    
    Parameters:
    canvas: ReportLab canvas object
    image_reader: ImageReader object
    x (float): X position (center)
    y (float): Y position (top)
    width (float): Desired width
    
    Returns:
    float: Height of the drawn image
    """
    try:
        if not image_reader:
            return 0
            
        # Get image dimensions
        img_width, img_height = image_reader.getSize()
        aspect_ratio = img_height / img_width
        height = width * aspect_ratio
        
        # Draw image centered at x, y
        canvas.drawImage(image_reader, x - (width / 2), y - height, width, height)
        
        logger.debug(f"Drew image: {width}x{height} at ({x}, {y})")
        return height
        
    except Exception as e:
        logger.warning(f"Failed to draw image: {e}")
        return 0

def create_pdf(output_path, title, canva_link, etsy_design_link=None, logo_url=None, flyer_image_url=None):
    """
    Create a PDF template with images and download links
    
    Parameters:
    output_path (str): Path where the PDF will be saved
    title (str): Title text for the PDF
    canva_link (str): Canva template download link
    etsy_design_link (str, optional): Etsy design service link
    logo_url (str, optional): URL to logo image
    flyer_image_url (str, optional): URL to flyer preview image
    
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
        current_y = height - 30
        
        # Define colors
        button_color = Color(0.2, 0.5, 0.8)  # Blue
        text_color = Color(0, 0, 0)  # Black
        white_color = Color(1, 1, 1)  # White
        
        # Download images if URLs provided
        logo_image = None
        flyer_image = None
        
        try:
            if logo_url and logo_url.strip():
                logo_image = download_image(logo_url)
                if logo_image:
                    logger.info("Logo image downloaded successfully")
                else:
                    logger.warning("Failed to download logo image")
        except Exception as e:
            logger.warning(f"Error downloading logo image: {e}")
        
        try:
            if flyer_image_url and flyer_image_url.strip():
                flyer_image = download_image(flyer_image_url)
                if flyer_image:
                    logger.info("Flyer image downloaded successfully")
                else:
                    logger.warning("Failed to download flyer image")
        except Exception as e:
            logger.warning(f"Error downloading flyer image: {e}")
        
        # Draw logo at the top if provided
        if logo_image:
            logo_height = draw_image(c, logo_image, width / 2, current_y, 100)
            current_y -= (logo_height + 20)
        
        # Title with [Template] suffix
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 18)
        title_text = f"{title} [Template]"
        c.drawCentredString(width / 2, current_y, title_text)
        current_y -= 30
        
        # Draw flyer image if provided
        if flyer_image:
            flyer_height = draw_image(c, flyer_image, width / 2, current_y, 350)
            current_y -= (flyer_height + 30)
        
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
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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

