# === pdf_compressor.py ===
# Created: September 18, 2025 - 12:00 PM
# Purpose: PDF compression functionality for reducing file sizes in cloud environment
# Key Exports:
#   - compress_pdf_file(): Main compression function using PyMuPDF approach
#   - get_file_size(): Utility for file size information
# Interactions:
#   - Used by: app.py for automatic PDF compression after generation
# Notes:
#   - Uses PyMuPDF (fitz) approach for cloud compatibility
#   - No Ghostscript dependency required

import os
import io
import logging
import tempfile
from pathlib import Path
from PIL import Image

# Configure logging
logger = logging.getLogger(__name__)

def check_dependencies():
    """
    Check if required dependencies are installed and install if missing
    
    Returns:
    bool: True if all dependencies are available
    """
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        return True
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        return False

def compress_image(image_data, quality=85, dpi=150):
    """
    Compress an image using PIL
    
    Parameters:
    image_data (bytes): Raw image data
    quality (int): JPEG quality (0-100, higher is better quality)
    dpi (int): Target DPI for the compressed image
    
    Returns:
    bytes: Compressed image data
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True, dpi=(dpi, dpi))
        return output.getvalue()
    
    except Exception as e:
        logger.warning(f"Failed to compress image: {e}")
        return image_data  # Return original if compression fails

def compress_pdf_file(input_file, output_file=None, compression_level=3):
    """
    Compress PDF file using PyMuPDF and PIL for image optimization
    
    Parameters:
    input_file (str): Path to the input PDF file
    output_file (str, optional): Path to the output PDF file
    compression_level (int): Compression level (0-4), higher means more compression
    
    Returns:
    str: Path to the compressed PDF file (may be same as input if no compression achieved)
    
    Raises:
    Exception: If compression fails
    """
    if not check_dependencies():
        logger.error("Required dependencies not available for PDF compression")
        return input_file
    
    import fitz  # PyMuPDF
    
    try:
        # Generate output filename if not provided
        if not output_file:
            path = Path(input_file)
            output_file = str(path.with_stem(f"{path.stem}_compressed"))
        
        # Quality settings based on compression level
        quality_settings = {
            0: {"quality": 95, "dpi": 300, "max_dimension": 4000},  # Minimal compression
            1: {"quality": 90, "dpi": 250, "max_dimension": 3000},  # Light compression
            2: {"quality": 85, "dpi": 200, "max_dimension": 2500},  # Medium compression
            3: {"quality": 75, "dpi": 150, "max_dimension": 2000},  # High compression
            4: {"quality": 60, "dpi": 100, "max_dimension": 1500}   # Maximum compression
        }
        
        settings = quality_settings.get(compression_level, quality_settings[3])
        quality = settings["quality"]
        dpi = settings["dpi"]
        max_dimension = settings["max_dimension"]
        
        logger.info(f"Compressing PDF: {input_file} (level {compression_level})")
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Open the PDF with PyMuPDF
            doc = fitz.open(input_file)
            images_compressed = False
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                # Process each image on the page
                for img_index, img_info in enumerate(image_list):
                    try:
                        xref = img_info[0]
                        
                        # Extract the image
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Skip very small images (likely icons or decorations)
                        if len(image_bytes) < 10000:  # Skip images smaller than ~10KB
                            continue
                        
                        # Try to open and process the image
                        img = Image.open(io.BytesIO(image_bytes))
                        
                        # Skip very small images in dimensions
                        if img.width < 100 or img.height < 100:
                            continue
                        
                        logger.debug(f"Processing image {img_index} on page {page_num}: {img.width}x{img.height}")
                        
                        # Convert RGBA to RGB if needed
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                        
                        # Calculate scaling if image is too large
                        current_max = max(img.width, img.height)
                        scale_factor = 1.0
                        
                        if current_max > max_dimension:
                            scale_factor = max_dimension / current_max
                            new_width = int(img.width * scale_factor)
                            new_height = int(img.height * scale_factor)
                            img = img.resize((new_width, new_height), Image.LANCZOS)
                            logger.debug(f"Resized image to: {new_width}x{new_height}")
                        
                        # Compress the image
                        output_buf = io.BytesIO()
                        img.save(output_buf, format='JPEG', quality=quality, optimize=True)
                        compressed_bytes = output_buf.getvalue()
                        
                        # Only replace if we achieved significant compression
                        compression_ratio = len(compressed_bytes) / len(image_bytes)
                        if compression_ratio < 0.95:  # At least 5% reduction
                            # Save compressed image to temporary file
                            img_path = os.path.join(temp_dir, f"img_{page_num}_{img_index}.jpg")
                            with open(img_path, "wb") as img_file:
                                img_file.write(compressed_bytes)
                            
                            # Get the original image rectangle
                            img_rect = page.get_image_rects(xref)[0] if page.get_image_rects(xref) else fitz.Rect(0, 0, 100, 100)
                            
                            # Remove original image and insert compressed version
                            page.delete_image(xref)
                            page.insert_image(img_rect, filename=img_path)
                            images_compressed = True
                            
                            logger.debug(f"Compressed image: {len(image_bytes)} -> {len(compressed_bytes)} bytes ({compression_ratio:.2%})")
                    
                    except Exception as e:
                        logger.warning(f"Failed to process image {img_index} on page {page_num}: {e}")
                        continue
            
            # Save the PDF with optimizations
            save_options = {
                "garbage": 4,      # Remove unused objects
                "deflate": True,   # Compress content streams
                "clean": True,     # Clean up document structure
                "ascii": False     # Use binary encoding
            }
            
            if images_compressed:
                doc.save(output_file, **save_options)
            else:
                # Even if no images were compressed, apply general PDF optimizations
                doc.save(output_file, **save_options)
            
            doc.close()
            
            # Check compression results
            input_size = os.path.getsize(input_file)
            output_size = os.path.getsize(output_file)
            
            if output_size < input_size:
                compression_ratio = (1 - (output_size / input_size)) * 100
                logger.info(f"PDF compressed successfully: {input_size/1024:.2f}KB -> {output_size/1024:.2f}KB ({compression_ratio:.2f}% reduction)")
                return output_file
            else:
                logger.info(f"Compression did not reduce file size, keeping original")
                # Remove the output file if it's not smaller
                if os.path.exists(output_file) and output_file != input_file:
                    os.remove(output_file)
                return input_file
    
    except Exception as e:
        logger.error(f"PDF compression failed for {input_file}: {e}")
        # Clean up output file if it was created
        if output_file and os.path.exists(output_file) and output_file != input_file:
            try:
                os.remove(output_file)
            except:
                pass
        return input_file

def get_file_size(file_path):
    """
    Get file size in a human-readable format
    
    Parameters:
    file_path (str): Path to the file
    
    Returns:
    dict: File size information with bytes, KB, and MB values
    """
    try:
        size_bytes = os.path.getsize(file_path)
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        
        return {
            'bytes': size_bytes,
            'kb': round(size_kb, 2),
            'mb': round(size_mb, 2),
            'human_readable': format_file_size(size_bytes)
        }
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        return {'bytes': 0, 'kb': 0, 'mb': 0, 'human_readable': 'Unknown'}

def format_file_size(size_bytes):
    """
    Format file size in human-readable format
    
    Parameters:
    size_bytes (int): File size in bytes
    
    Returns:
    str: Formatted file size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
