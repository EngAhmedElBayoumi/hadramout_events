import os
import io
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from django.conf import settings
from django.contrib.staticfiles import finders
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import arabic_reshaper
from bidi.algorithm import get_display

def _register_arabic_fonts():
    """
    Register an Arabic-capable font with graceful fallbacks.
    """
    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "DejaVuSans",
            "DejaVuSans-Bold",
        ),
        (
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
            "NotoNaskhArabic",
            "NotoNaskhArabic-Bold",
        ),
    ]

    for regular_path, bold_path, regular_name, bold_name in candidates:
        if os.path.exists(regular_path) and os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont(regular_name, regular_path))
            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
            return regular_name, bold_name

    return "Helvetica", "Helvetica-Bold"


DEFAULT_FONT, BOLD_FONT = _register_arabic_fonts()


def _get_logo_path():
    """Resolve logo from staticfiles (works with collectstatic) with fallback."""
    static_logo = finders.find("logo.png")
    if static_logo and os.path.exists(static_logo):
        return static_logo

    fallback_logo = os.path.join(settings.BASE_DIR, "static", "logo.png")
    if os.path.exists(fallback_logo):
        return fallback_logo

    return None

def reshape_arabic(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def generate_doctor_card_pdf(queryset, request=None):
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
    logo_path = _get_logo_path()

    # Get current domain for QR code
    domain = ""
    if request:
        domain = f"{request.scheme}://{request.get_host()}"

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
        if logo_path:
            logo_w = 30 * mm
            logo_h = 30 * mm
            # Draw logo centered inside the circular badge
            c.drawImage(
                logo_path,
                circle_x - (logo_w / 2),
                circle_y - (logo_h / 2),
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask='auto',
            )
        
        # 4. QR Code on the right
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr_url = doctor.get_qr_code_url()
        if domain:
            qr_url = f"{domain}{qr_url}"
        qr.add_data(qr_url)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        qr_io = io.BytesIO()
        img_qr.save(qr_io)
        qr_io.seek(0)
        
        qr_size = 22 * mm
        c.drawImage(ImageReader(qr_io), x + card_w - 30 * mm, y + 23 * mm, width=qr_size, height=qr_size)

        # 5. Doctor Info Text
        c.setFillColor(HexColor("#000000"))
        c.setFont(BOLD_FONT, 13)
        # Handle Arabic name - Draw Dr. and Name separately to avoid RTL issues with mixed text
        c.drawString(x + 6 * mm, y + 20 * mm, "Dr. ")
        name_x = x + 6 * mm + c.stringWidth("Dr. ", BOLD_FONT, 13)
        c.drawString(name_x, y + 20 * mm, reshape_arabic(doctor.name))
        
        c.setFont(DEFAULT_FONT, 10)
        specialty_name = doctor.specialty.name if doctor.specialty else "General"
        c.drawString(x + 6 * mm, y + 14 * mm, "Specialization: ")
        spec_x = x + 6 * mm + c.stringWidth("Specialization: ", DEFAULT_FONT, 10)
        c.drawString(spec_x, y + 14 * mm, reshape_arabic(specialty_name))
        
        phone_text = f"Phone: {doctor.phone}"
        c.drawString(x + 6 * mm, y + 9 * mm, phone_text)

        # 6. Red stripe at bottom
        c.setFillColor(red_color)
        c.rect(x, y, card_w, 4 * mm, fill=1, stroke=0)

        # --- BACK ---
        # Move to next slot for back side (or same slot on next page if duplex)
        # For simplicity, we put it below the front
        y -= (card_h + 5 * mm)
        
        c.setFillColor(red_color)
        c.rect(x, y, card_w, card_h, fill=1, stroke=0)
        
        if logo_path:
            logo_center_w = 40 * mm
            logo_center_h = 24 * mm
            c.drawImage(
                logo_path,
                x + (card_w - logo_center_w) / 2,
                y + (card_h - logo_center_h) / 2,
                width=logo_center_w,
                height=logo_center_h,
                preserveAspectRatio=True,
                mask='auto',
            )

        # Move to next pair position
        y -= (card_h + 15 * mm)
        if y < margin + card_h:
            c.showPage()
            y = height - margin - card_h

    c.save()
    buffer.seek(0)
    return buffer
