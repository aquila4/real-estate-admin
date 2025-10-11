import os
import shutil

# Ensure brochure folder exists
os.makedirs("static/brochure", exist_ok=True)

# Path to your existing ready-made graphic brochure
source_pdf = "static/graphics/Great-Marcy-Brochure.pdf"  # <-- put your designed PDF here
destination_pdf = "static/brochure/Great-Marcy-Brochure.pdf"

# Copy the existing brochure to the output folder
if os.path.exists(source_pdf):
    shutil.copy(source_pdf, destination_pdf)
    print(f"✅ Graphic brochure copied to: {destination_pdf}")
else:
    print("⚠️ Brochure source file not found. Please make sure it’s located at:")
    print("   static/graphics/Great-Marcy-Brochure.pdf")
