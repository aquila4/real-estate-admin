from fpdf import FPDF
import os

# Ensure brochure folder exists
os.makedirs("static/brochure", exist_ok=True)

# Initialize PDF
pdf = FPDF(orientation='P', unit='mm', format='A4')
pdf.add_page()

# Add only regular Unicode font
pdf.add_font("DejaVu", "", "static/fonts/DejaVuSans.ttf", uni=True)
pdf.set_font("DejaVu", "", 12)

# Add logo
logo_path = "static/images/logogmc.png"
if os.path.exists(logo_path):
    pdf.image(logo_path, x=80, y=pdf.get_y(), w=50)
    pdf.ln(40)

# Title
pdf.set_text_color(0, 51, 102)
pdf.cell(0, 12, "Great Marcys & Sons Limited", ln=True, align="C")
pdf.ln(5)

# Subtitle
pdf.cell(0, 10, "Find Your Property in Nigeria", ln=True, align="C")
pdf.ln(10)

# Introduction
pdf.cell(0, 10, "Introduction", ln=True)
intro_text = "Great Marcy & Sons, we don’t just sell properties — we build trust, stability, and a shared future for every client."
pdf.multi_cell(0, 8, intro_text)
pdf.ln(5)

# Featured Estates
pdf.set_text_color(0, 51, 102)
pdf.cell(0, 10, "Our Featured Estates", ln=True)
featured = [
    "Success City Estate",
    "His Grace City Estate Phase 1",
    "His Grace City Estate Phase 2"
]
for estate in featured:
    pdf.cell(5)
    pdf.cell(0, 8, f"- {estate}", ln=True)
pdf.ln(5)

# Core Values
pdf.cell(0, 10, "Our Core Values", ln=True)
core_values = {
    "Trust": "Trust is the foundation of everything we do...",
    "Customer-Centricity": "We put clients first...",
    "Innovation": "We redefine what's possible...",
    "Excellence": "We deliver the best...",
    "Transparency": "Open and honest transactions..."
}
for key, value in core_values.items():
    pdf.cell(0, 8, f"{key}:", ln=True)
    pdf.multi_cell(0, 8, value)
    pdf.ln(2)

# Vision
pdf.set_text_color(0, 51, 102)
pdf.cell(0, 10, "Our Vision", ln=True)
vision_text = "To be the premier real estate company in Ilorin and beyond, helping clients find their dream properties with confidence."
pdf.multi_cell(0, 8, vision_text)
pdf.ln(10)

# Contact
pdf.set_text_color(0, 0, 0)
pdf.cell(0, 8, "Contact us: +234 913 907 0404 | info@greatmarcysonslimited.com", ln=True, align="C")
pdf.cell(0, 8, "Address: KULENDE AREA, KM5 OLD JEBBA ROAD, Sango Rd, Ilorin 240101, Kwara", ln=True, align="C")

# Save PDF
output_path = "static/brochure/Great-Marcy-Brochure.pdf"
pdf.output(output_path)
print(f"Brochure generated at {output_path}")
