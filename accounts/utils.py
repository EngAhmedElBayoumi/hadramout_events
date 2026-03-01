import os
import io
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
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
        # Windows
        (
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "Arial",
            "Arial-Bold",
        ),
        (
            "C:\\Windows\\Fonts\\tahoma.ttf",
            "C:\\Windows\\Fonts\\tahomabd.ttf",
            "Tahoma",
            "Tahoma-Bold",
        ),
        # Linux
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
        if os.path.exists(regular_path):
            try:
                pdfmetrics.registerFont(TTFont(regular_name, regular_path))
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                    return regular_name, bold_name
                return regular_name, regular_name
            except Exception:
                continue

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
    dark_gray = HexColor("#333333")
    logo_path = _get_logo_path()

    # Restaurant contact info
    restaurant_address = reshape_arabic("ميت غمر شارع بورسعيد اعلي فودافون")
    restaurant_phones = "01281544483 - 050/4933243 - 01058599939 - 01156363866"

    # Get current domain for QR code
    domain = ""
    if request:
        domain = f"{request.scheme}://{request.get_host()}"

    for doctor in queryset:
        # --- FRONT ---
        # 1. Background (Main Area)
        c.setFillColor(bg_color)
        c.setStrokeColor(white)
        c.setLineWidth(1.5)
        c.rect(x, y, card_w, card_h, fill=1, stroke=1)
        
        # 2. Sidebar (Maroon left background)
        sidebar_w = 22 * mm
        c.setFillColor(red_color)
        c.rect(x, y, sidebar_w, card_h, fill=1, stroke=0)
        
        # 3. Sidebar Elements: Logo & QR
        # --- Logo with white circular border ---
        logo_center_x = x + sidebar_w / 2
        logo_center_y = y + card_h - 12 * mm
        
        if logo_path:
            # Draw thin white circle border around logo
            logo_radius = 7 * mm
            c.setFillColor(white)
            c.setStrokeColor(white)
            c.setLineWidth(0.6)
            c.circle(logo_center_x, logo_center_y, logo_radius, fill=0, stroke=1)
            
            logo_w = 18 * mm
            logo_h = 11 * mm
            c.drawImage(
                logo_path,
                logo_center_x - (logo_w / 2),
                logo_center_y - (logo_h / 2),
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask='auto',
            )
            
        # --- QR Code in Sidebar (Black on white square) ---
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr_url = doctor.get_qr_code_url()
        if domain:
            qr_url = f"{domain}{qr_url}"
        qr.add_data(qr_url)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white") # Black on white
        qr_io = io.BytesIO()
        img_qr.save(qr_io)
        qr_io.seek(0)
        
        qr_size = 18 * mm
        # Draw white background for QR
        c.setFillColor(white)
        qr_bg_padding = 1 * mm
        c.rect(x + (sidebar_w - qr_size)/2 - qr_bg_padding, y + 6 * mm - qr_bg_padding, qr_size + qr_bg_padding*2, qr_size + qr_bg_padding*2, fill=1, stroke=0)
        c.drawImage(ImageReader(qr_io), x + (sidebar_w - qr_size)/2, y + 6 * mm, width=qr_size, height=qr_size)

        # 4. Main Area Content (Doctor Info)
        # Position offset from sidebar
        info_x = x + sidebar_w + 6 * mm
        max_text_w = card_w - sidebar_w - 12 * mm # Padding limit
        
        # --- Name (Large, Bold, Maroon, AUTO-SCALE) ---
        c.setFillColor(red_color)
        name_text = f"Dr. {doctor.name}"
        reshaped_name = reshape_arabic(name_text)
        
        # Auto-scale font size
        name_font_size = 14
        while c.stringWidth(reshaped_name, BOLD_FONT, name_font_size) > max_text_w and name_font_size > 8:
            name_font_size -= 0.5
            
        c.setFont(BOLD_FONT, name_font_size)
        c.drawString(info_x, y + 34 * mm, reshaped_name)
        
        # --- Specialization (Medium, Regular, Dark Gray) ---
        c.setFillColor(dark_gray)
        c.setFont(DEFAULT_FONT, 10.5)
        specialty_name = doctor.specialty.name if doctor.specialty else "General"
        label_spec = "Specialization: "
        reshaped_spec = reshape_arabic(f"{label_spec}{specialty_name}")
        c.drawString(info_x, y + 26 * mm, reshaped_spec)
        
        # --- Phone (Small, Regular, Dark Gray) ---
        c.setFont(DEFAULT_FONT, 9.5)
        phone_text = f"Phone: {doctor.phone}"
        c.drawString(info_x, y + 20 * mm, phone_text)

        # 5. Restaurant contact info on front (inside card, above bottom strip)
        # Info area at bottom of main section
        info_area_x = x + sidebar_w  # Start after sidebar
        info_area_w = card_w - sidebar_w
        c.setFillColor(dark_gray)
        c.setFont(DEFAULT_FONT, 5)
        # Address - centered in main area
        addr_w = c.stringWidth(restaurant_address, DEFAULT_FONT, 5)
        c.drawString(info_area_x + (info_area_w - addr_w) / 2, y + 10 * mm, restaurant_address)
        # Phones - centered in main area
        phones_w = c.stringWidth(restaurant_phones, DEFAULT_FONT, 4.5)
        c.setFont(DEFAULT_FONT, 4.5)
        c.drawString(info_area_x + (info_area_w - phones_w) / 2, y + 7 * mm, restaurant_phones)

        # Bottom Detail (Thin closing line)
        c.setFillColor(red_color)
        c.rect(x, y, card_w, 4 * mm, fill=1, stroke=0)

        # --- BACK SIDE ---
        # Same slot logic
        y_back = y - (card_h + 5 * mm)
        c.setFillColor(red_color)
        c.setStrokeColor(white)
        c.setLineWidth(1.5)
        c.rect(x, y_back, card_w, card_h, fill=1, stroke=1)
        
        if logo_path:
            # Draw thin white circle border around logo on back
            back_logo_cx = x + card_w / 2
            back_logo_cy = y_back + card_h / 2 + 5 * mm
            back_logo_radius = 14 * mm
            c.setStrokeColor(white)
            c.setLineWidth(0.9)
            c.circle(back_logo_cx, back_logo_cy, back_logo_radius, fill=0, stroke=1)

            logo_center_w = 40 * mm
            logo_center_h = 24 * mm
            c.drawImage(
                logo_path,
                x + (card_w - logo_center_w) / 2,
                y_back + (card_h - logo_center_h) / 2 + 5 * mm,
                width=logo_center_w,
                height=logo_center_h,
                preserveAspectRatio=True,
                mask='auto',
            )

        # Restaurant contact info on back (bottom center)
        c.setFillColor(white)
        c.setFont(DEFAULT_FONT, 5.5)
        addr_w_back = c.stringWidth(restaurant_address, DEFAULT_FONT, 5.5)
        c.drawString(x + (card_w - addr_w_back) / 2, y_back + 8 * mm, restaurant_address)
        c.setFont(DEFAULT_FONT, 5)
        phones_w_back = c.stringWidth(restaurant_phones, DEFAULT_FONT, 5)
        c.drawString(x + (card_w - phones_w_back) / 2, y_back + 4.5 * mm, restaurant_phones)

        # Move to next pair position (Move Y down by 2 cards + spacing)
        y -= (card_h * 2 + 15 * mm)
        if y < margin + card_h:
            c.showPage()
            y = height - margin - card_h

    c.save()
    buffer.seek(0)
    return buffer
