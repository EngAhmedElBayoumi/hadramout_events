import os
import io
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register a font that supports Arabic if available, else fallback
# For now, we use standard fonts, but for Arabic text it will be tricky.
# I'll try to find a font in the system or just use standard.
# Standard fonts don't support Arabic well. 

def generate_doctor_card_pdf(queryset):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Card dimensions: 85mm x 55mm
    card_w = 85 * mm
    card_h = 55 * mm
    
    # Margin and spacing
    margin = 15 * mm
    x = margin
    y = height - margin - card_h

    # Colors
    bg_color = HexColor("#F5ECD7") # Cream/Beige
    red_color = HexColor("#A02020")
    white_color = HexColor("#FFFFFF")

    for doctor in queryset:
        # --- FRONT ---
        # 1. Background
        c.setFillColor(bg_color)
        c.rect(x, y, card_w, card_h, fill=1, stroke=0)
        
        # 2. Red Circle for Logo
        circle_x = x + 15 * mm
        circle_y = y + card_h - 15 * mm
        circle_r = 12 * mm
        c.setFillColor(red_color)
        c.circle(circle_x, circle_y, circle_r, fill=1, stroke=0)
        
        # 3. Logo inside circle
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'logo.png')
        if os.path.exists(logo_path):
            # We want to center the logo in the circle. 
            # Logo is usually wider than high.
            logo_w = 18 * mm
            c.drawImage(logo_path, circle_x - logo_w/2, circle_y - 6 * mm, width=logo_w, preserveAspectRatio=True, mask='auto')
        
        # 4. QR Code on the right
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(doctor.qr_code)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white") # Back to white for contrast or transparent?
        qr_io = io.BytesIO()
        img_qr.save(qr_io)
        qr_io.seek(0)
        
        from reportlab.lib.utils import ImageReader
        qr_size = 22 * mm
        c.drawImage(ImageReader(qr_io), x + card_w - 30 * mm, y + 23 * mm, width=qr_size, height=qr_size)

        # 5. Doctor Info Text
        c.setFillColor(HexColor("#000000"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x + 5 * mm, y + 18 * mm, f"Dr. {doctor.name}")
        
        c.setFont("Helvetica", 9)
        specialty_name = doctor.specialty.name if doctor.specialty else "General"
        c.drawString(x + 5 * mm, y + 13 * mm, f"Specialization: {specialty_name}")
        c.drawString(x + 5 * mm, y + 8 * mm, f"Phone: {doctor.phone}")

        # 6. Red stripe at bottom
        c.setFillColor(red_color)
        c.rect(x, y, card_w, 4 * mm, fill=1, stroke=0)

        # --- NEXT SLOT or NEW PAGE ---
        y -= (card_h + 10 * mm)
        
        # --- BACK ---
        c.setFillColor(red_color)
        c.rect(x, y, card_w, card_h, fill=1, stroke=0)
        
        if os.path.exists(logo_path):
            # Center logo on red background
            # Note: The logo might need white brightness or inversion if it's dark
            # But here we just draw it.
            logo_center_w = 45 * mm
            c.drawImage(logo_path, x + (card_w - logo_center_w) / 2, y + (card_h - 20 * mm) / 2, width=logo_center_w, preserveAspectRatio=True, mask='auto')

        # Move to next pair position
        y -= (card_h + 15 * mm)
        if y < margin + card_h:
            c.showPage()
            y = height - margin - card_h

    c.save()
    buffer.seek(0)
    return buffer
