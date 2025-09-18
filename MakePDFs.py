import csv
import os
from tkinter import Tk, filedialog
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image

# Function to add an image to the PDF
def draw_image(c, image_path, x, y, width):
    try:
        img = Image.open(image_path)
        aspect_ratio = img.height / img.width
        height = width * aspect_ratio
        c.drawImage(image_path, x - (width / 2), y - height, width, height)
        return height  # Return height of the image for proper positioning
    except Exception as e:
        print(f"Error adding image {image_path}: {e}")
        return 0

# Hardcoded Etsy links
ETSY_DESIGN_LINK = "https://www.etsy.com/listing/1827167654/custom-flyer-design-party-flyer-canva"
ETSY_EDIT_LINK = "https://www.etsy.com/listing/1827168460/custom-flyer-edits-and-design-party"

# Function to create a PDF
def create_pdf(output_path, title, logo_path, flyer_image_path, canva_link):
    # Create a canvas
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    current_y = height - 30  # Start drawing closer to the top with reduced margin

    # Draw the logo at the top center (100px width)
    logo_height = draw_image(c, logo_path, width / 2, current_y, 100)
    current_y -= (logo_height + 10)  # Reduced spacing below the logo

    # Title with [Template] suffix
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, current_y, f"{title} [Template]")
    current_y -= 20  # Shortened spacing below the title

    # Draw the flyer image (scaled down by 10-15%)
    flyer_height = draw_image(c, flyer_image_path, width / 2, current_y, 350)  # Reduced width from 400 to 350
    current_y -= (flyer_height + 25)  # Added more spacing below the flyer image

    # "Thank You" message and download button
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, current_y, "Thank you for your purchase!")
    current_y -= 20
    c.drawCentredString(width / 2, current_y, "Click the button below to download and edit your template.")
    current_y -= 40  # Increased spacing between this line and the button

    # Main Canva link button
    c.setFillColorRGB(0.2, 0.5, 0.8)  # Button color
    c.rect(150, current_y, 300, 30, fill=1)
    c.setFillColorRGB(1, 1, 1)  # Text color
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, current_y + 10, "Download & Edit Template")
    c.linkURL(canva_link, (150, current_y, 450, current_y + 30), relative=0)
    current_y -= 50  # Increased spacing below the main button

    # Etsy links
    # Button 1: Customization Help
    c.setFillColorRGB(0.2, 0.5, 0.8)  # Button color
    c.rect(150, current_y, 140, 25, fill=1)
    c.setFillColorRGB(1, 1, 1)  # Text color
    c.drawCentredString(220, current_y + 8, "Customization Help")
    c.linkURL(ETSY_EDIT_LINK, (150, current_y, 290, current_y + 25), relative=0)

    # Button 2: Custom Flyers
    c.setFillColorRGB(0.2, 0.5, 0.8)  # Button color
    c.rect(310, current_y, 140, 25, fill=1)
    c.setFillColorRGB(1, 1, 1)  # Text color
    c.drawCentredString(380, current_y + 8, "Custom Flyers")
    c.linkURL(ETSY_DESIGN_LINK, (310, current_y, 450, current_y + 25), relative=0)
    current_y -= 40  # Reduced spacing below the buttons

    # Descriptive text for buttons
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0, 0, 0)  # Black text
    c.drawCentredString(
        width / 2,
        current_y,
        "Need help customizing this flyer or want a completely custom flyer idea done? Click the buttons above!",
    )
    current_y -= 40

    # Footer message
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width / 2, current_y, "We appreciate you as our customer! Your 5-star reviews mean the world to us!")

    # Save the PDF
    c.save()

# Function to process the CSV and create PDFs
def process_csv_and_create_pdfs():
    # Open a file dialog to select the CSV file
    Tk().withdraw()  # Hide the root Tkinter window
    csv_file_path = filedialog.askopenfilename(
        title="Select CSV File",
        filetypes=[("CSV Files", "*.csv")]
    )

    if not csv_file_path:
        print("No CSV file selected. Exiting.")
        return

    # Open a file dialog to select the logo file
    logo_file_path = filedialog.askopenfilename(
        title="Select Logo File",
        filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")]
    )

    if not logo_file_path:
        print("No logo file selected. Exiting.")
        return

    with open(csv_file_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Extract data from CSV
            title = row["Title"]
            flyer_image_path = row["imageName"]
            canva_link = row["canvaLink"]

            # Derive folder path and output PDF name
            folder_path = os.path.dirname(flyer_image_path)
            folder_name = os.path.basename(folder_path)

            # Ensure folder_name is not longer than 25 characters
            if len(folder_name) > 25:
                folder_name = folder_name[:22] + "..."  # Truncate and add ellipsis

            pdf_name = f"{folder_name} [Template].pdf"
            pdf_path = os.path.join(folder_path, pdf_name)

            # Create the PDF
            create_pdf(pdf_path, title, logo_file_path, flyer_image_path, canva_link)

# Run the script
process_csv_and_create_pdfs()
