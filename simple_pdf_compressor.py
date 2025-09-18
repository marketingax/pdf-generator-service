#!/usr/bin/env python3
"""
Simple PDF Compressor - A basic tool to compress PDF files without Ghostscript
"""

import os
import sys
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import subprocess
import tempfile
import io
from PIL import Image

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import PyPDF2
        from PIL import Image
    except ImportError:
        print("Installing required dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2", "Pillow"])
        print("Dependencies installed successfully!")
    
    # Check for PyMuPDF
    try:
        import fitz
    except ImportError:
        print("Installing PyMuPDF...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF"])
        print("PyMuPDF installed successfully!")
    
    return True

def compress_image(image_data, quality=85, dpi=150):
    """Compress an image using PIL"""
    img = Image.open(io.BytesIO(image_data))
    
    # Convert RGBA to RGB if needed
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True, dpi=(dpi, dpi))
    return output.getvalue()

def compress_pdf(input_file, output_file=None, power=3):
    """
    Compress PDF file using PyPDF2 and PIL
    
    Parameters:
    input_file (str): Path to the input PDF file
    output_file (str, optional): Path to the output PDF file
    power (int): Compression level (0-4), higher means more compression
    
    Returns:
    str: Path to the compressed PDF file
    """
    import PyPDF2
    import fitz  # PyMuPDF
    import io
    from PIL import Image
    
    if not output_file:
        path = Path(input_file)
        output_file = str(path.with_stem(f"{path.stem}_compressed.pdf"))
    
    # Quality settings based on power level
    quality_settings = {
        0: {"quality": 95, "dpi": 300},  # Minimal compression
        1: {"quality": 90, "dpi": 250},  # Light compression
        2: {"quality": 85, "dpi": 200},  # Medium compression
        3: {"quality": 75, "dpi": 150},  # High compression
        4: {"quality": 60, "dpi": 100}   # Maximum compression
    }
    
    quality = quality_settings[power]["quality"]
    dpi = quality_settings[power]["dpi"]
    
    try:
        # Create a temporary directory for image processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Open the PDF with PyMuPDF
            doc = fitz.open(input_file)
            
            # Track if we've compressed any images
            images_compressed = False
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                # Process each image on the page
                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    
                    # Extract the image
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Skip small images (likely icons or decorations)
                    if len(image_bytes) < 10000:  # Skip images smaller than ~10KB
                        continue
                    
                    # Try to open and compress the image
                    try:
                        img = Image.open(io.BytesIO(image_bytes))
                        
                        # Skip very small images in dimensions
                        if img.width < 100 or img.height < 100:
                            continue
                        
                        # Convert RGBA to RGB if needed
                        if img.mode == 'RGBA':
                            img = img.convert('RGB')
                        
                        # Calculate new dimensions while maintaining aspect ratio
                        max_dimension = max(img.width, img.height)
                        scale_factor = 1.0
                        
                        # Scale down large images based on compression level
                        if power >= 3 and max_dimension > 1500:
                            scale_factor = 1500 / max_dimension
                        elif power >= 2 and max_dimension > 2000:
                            scale_factor = 2000 / max_dimension
                        elif power >= 1 and max_dimension > 3000:
                            scale_factor = 3000 / max_dimension
                        
                        if scale_factor < 1.0:
                            new_width = int(img.width * scale_factor)
                            new_height = int(img.height * scale_factor)
                            img = img.resize((new_width, new_height), Image.LANCZOS)
                        
                        # Compress the image
                        output_buf = io.BytesIO()
                        img.save(output_buf, format='JPEG', quality=quality, optimize=True)
                        compressed_bytes = output_buf.getvalue()
                        
                        # Only replace if we achieved compression
                        if len(compressed_bytes) < len(image_bytes):
                            # Save the compressed image to a temporary file
                            img_path = os.path.join(temp_dir, f"img_{page_num}_{img_index}.jpg")
                            with open(img_path, "wb") as img_file:
                                img_file.write(compressed_bytes)
                            
                            # Replace the image in the PDF
                            page.delete_image(xref)
                            rect = page.insert_image(img_info[1], filename=img_path)
                            images_compressed = True
                    
                    except Exception as e:
                        print(f"Error processing image: {e}")
                        continue
            
            # Save the PDF with compressed images if any were compressed
            if images_compressed:
                doc.save(output_file, garbage=4, deflate=True, clean=True)
                doc.close()
                
                # Check if the compressed file is actually smaller
                input_size = os.path.getsize(input_file)
                output_size = os.path.getsize(output_file)
                
                if output_size < input_size:
                    compression_ratio = (1 - (output_size / input_size)) * 100
                    print(f"Compressed {input_file} from {input_size/1024:.2f}KB to {output_size/1024:.2f}KB ({compression_ratio:.2f}% reduction)")
                    result = output_file
                else:
                    print(f"Compression did not reduce file size for {input_file}. Keeping original.")
                    if os.path.exists(output_file):
                        os.remove(output_file)
                    result = input_file
            else:
                # Try another approach with PyPDF2 if no images were compressed
                print(f"No compressible images found in {input_file}, trying alternative method...")
                
                # Create a temporary file for the output
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_filename = temp_file.name
                
                # Use PyPDF2 to compress
                with open(input_file, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    writer = PyPDF2.PdfWriter()
                    
                    # Process each page
                    for page_num in range(len(reader.pages)):
                        page = reader.pages[page_num]
                        writer.add_page(page)
                    
                    # Use compression
                    writer.add_metadata(reader.metadata)
                    
                    # Write the output file with compression
                    with open(temp_filename, 'wb') as output:
                        writer.write(output)
                
                # Check if the compressed file is actually smaller
                input_size = os.path.getsize(input_file)
                output_size = os.path.getsize(temp_filename)
                
                if output_size < input_size:
                    # Copy the compressed file to the output location
                    with open(temp_filename, 'rb') as f_in:
                        with open(output_file, 'wb') as f_out:
                            f_out.write(f_in.read())
                    
                    compression_ratio = (1 - (output_size / input_size)) * 100
                    print(f"Compressed {input_file} from {input_size/1024:.2f}KB to {output_size/1024:.2f}KB ({compression_ratio:.2f}% reduction)")
                    result = output_file
                else:
                    print(f"Compression did not reduce file size for {input_file}. Keeping original.")
                    result = input_file
                
                # Clean up the temporary file
                if os.path.exists(temp_filename):
                    os.unlink(temp_filename)
        
        return result
            
    except Exception as e:
        print(f"Error: Failed to compress {input_file}. {str(e)}")
        return input_file

def process_files(files, output_dir=None, compression_level=3):
    """Process multiple PDF files"""
    results = []
    
    for file_path in files:
        if not file_path.lower().endswith('.pdf'):
            print(f"Skipping {file_path} - not a PDF file")
            continue
        
        if output_dir:
            output_file = os.path.join(output_dir, os.path.basename(file_path).replace('.pdf', '_compressed.pdf'))
        else:
            output_file = None
        
        result = compress_pdf(file_path, output_file, compression_level)
        results.append((file_path, result))
    
    return results

def process_directory(directory, output_dir=None, compression_level=3, recursive=False):
    """Process all PDF files in a directory"""
    pdf_files = []
    
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
    else:
        pdf_files = [os.path.join(directory, f) for f in os.listdir(directory) 
                    if f.lower().endswith('.pdf') and os.path.isfile(os.path.join(directory, f))]
    
    return process_files(pdf_files, output_dir, compression_level)

def create_gui():
    """Create a simple GUI for the PDF compressor"""
    root = tk.Tk()
    root.title("Simple PDF Compressor")
    root.geometry("500x400")
    root.resizable(True, True)
    
    # Set padding and styling
    padding = {'padx': 10, 'pady': 10}
    
    # Frame for input selection
    input_frame = tk.Frame(root)
    input_frame.pack(fill=tk.X, **padding)
    
    tk.Label(input_frame, text="Select PDF files or a directory:").pack(anchor=tk.W)
    
    # Variables
    selected_files = []
    selected_dir = tk.StringVar()
    is_recursive = tk.BooleanVar(value=True)  # Set to True by default
    compression_level = tk.IntVar(value=3)
    output_directory = tk.StringVar()
    
    # Function to update the file list display
    def update_file_list():
        files_listbox.delete(0, tk.END)
        for file in selected_files:
            files_listbox.insert(tk.END, os.path.basename(file))
    
    # Button functions
    def select_files():
        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if files:
            selected_files.clear()
            selected_files.extend(files)
            selected_dir.set("")
            update_file_list()
    
    def select_directory():
        directory = filedialog.askdirectory(title="Select Directory with PDFs")
        if directory:
            selected_dir.set(directory)
            selected_files.clear()
            update_file_list()
            
            # Show files in the directory
            files_listbox.delete(0, tk.END)
            pdf_count = 0
            
            if is_recursive.get():
                for root, _, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            pdf_count += 1
                            if pdf_count <= 100:  # Limit display to 100 files
                                files_listbox.insert(tk.END, os.path.join(os.path.relpath(root, directory), file))
            else:
                for file in os.listdir(directory):
                    if file.lower().endswith('.pdf') and os.path.isfile(os.path.join(directory, file)):
                        pdf_count += 1
                        if pdf_count <= 100:
                            files_listbox.insert(tk.END, file)
            
            if pdf_count > 100:
                files_listbox.insert(tk.END, f"... and {pdf_count - 100} more PDF files")
            
            if pdf_count == 0:
                files_listbox.insert(tk.END, "No PDF files found in this directory")
    
    def select_output_dir():
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            output_directory.set(directory)
    
    # Buttons for file/directory selection
    buttons_frame = tk.Frame(input_frame)
    buttons_frame.pack(fill=tk.X, pady=5)
    
    tk.Button(buttons_frame, text="Select Files", command=select_files).pack(side=tk.LEFT, padx=5)
    tk.Button(buttons_frame, text="Select Directory", command=select_directory).pack(side=tk.LEFT, padx=5)
    
    # Recursive checkbox - make it more prominent
    recursive_frame = tk.Frame(input_frame, pady=5)
    recursive_frame.pack(fill=tk.X)
    recursive_checkbox = tk.Checkbutton(
        recursive_frame, 
        text="Include subdirectories (process all PDFs in subfolders)", 
        variable=is_recursive,
        font=("Arial", 10, "bold")
    )
    recursive_checkbox.pack(anchor=tk.W)
    
    # Files list
    list_frame = tk.Frame(root)
    list_frame.pack(fill=tk.BOTH, expand=True, **padding)
    
    tk.Label(list_frame, text="Files to compress:").pack(anchor=tk.W)
    
    files_listbox = tk.Listbox(list_frame)
    files_listbox.pack(fill=tk.BOTH, expand=True)
    
    # Compression options
    options_frame = tk.Frame(root)
    options_frame.pack(fill=tk.X, **padding)
    
    tk.Label(options_frame, text="Compression Level:").pack(anchor=tk.W)
    
    levels = [
        ("Low (Better Quality)", 1),
        ("Medium", 2),
        ("High (Recommended)", 3),
        ("Very High (Lower Quality)", 4)
    ]
    
    for text, value in levels:
        tk.Radiobutton(options_frame, text=text, variable=compression_level, value=value).pack(anchor=tk.W)
    
    # Output directory
    output_frame = tk.Frame(root)
    output_frame.pack(fill=tk.X, **padding)
    
    tk.Label(output_frame, text="Output Directory (optional):").pack(anchor=tk.W)
    
    output_dir_frame = tk.Frame(output_frame)
    output_dir_frame.pack(fill=tk.X, pady=5)
    
    tk.Entry(output_dir_frame, textvariable=output_directory).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    tk.Button(output_dir_frame, text="Browse", command=select_output_dir).pack(side=tk.RIGHT)
    
    # Compress button
    def start_compression():
        if not selected_files and not selected_dir.get():
            messagebox.showerror("Error", "Please select PDF files or a directory")
            return
        
        output_dir = output_directory.get() if output_directory.get() else None
        
        # Create output directory if it doesn't exist
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        try:
            results = []
            
            if selected_dir.get():
                results = process_directory(
                    selected_dir.get(), 
                    output_dir, 
                    compression_level.get(),
                    is_recursive.get()
                )
            else:
                results = process_files(selected_files, output_dir, compression_level.get())
            
            # Show results
            success_count = sum(1 for _, result in results if result != "")
            messagebox.showinfo(
                "Compression Complete", 
                f"Successfully compressed {success_count} out of {len(results)} files."
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    tk.Button(
        root, 
        text="Compress PDFs", 
        command=start_compression,
        bg="#4CAF50", 
        fg="white", 
        font=("Arial", 12, "bold"),
        pady=10
    ).pack(fill=tk.X, **padding)
    
    # Status bar
    status_bar = tk.Label(root, text="Ready (Simple Version - No Ghostscript Required)", bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    root.mainloop()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Compress PDF files to reduce file size (Simple Version)")
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("-f", "--files", nargs="+", help="PDF files to compress")
    input_group.add_argument("-d", "--directory", help="Directory containing PDF files")
    
    # Other options
    parser.add_argument("-o", "--output-dir", help="Output directory for compressed files")
    parser.add_argument("-r", "--recursive", action="store_true", default=True, help="Process directories recursively (default: enabled)")
    parser.add_argument("-l", "--level", type=int, choices=range(5), default=3, 
                        help="Compression level (0-4, higher means more compression)")
    parser.add_argument("-g", "--gui", action="store_true", help="Launch the graphical user interface")
    
    args = parser.parse_args()
    
    # Check dependencies
    check_dependencies()
    
    # Launch GUI if requested or if no arguments provided
    if args.gui or (not args.files and not args.directory):
        create_gui()
        return
    
    # Process files or directory
    if args.files:
        results = process_files(args.files, args.output_dir, args.level)
    elif args.directory:
        results = process_directory(args.directory, args.output_dir, args.level, args.recursive)
    
    # Print summary
    print("\nCompression Summary:")
    success_count = sum(1 for _, result in results if result != "")
    print(f"Successfully compressed {success_count} out of {len(results)} files.")

if __name__ == "__main__":
    main() 