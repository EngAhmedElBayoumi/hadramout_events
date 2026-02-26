from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.http import Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts.models import Doctor


class QRCodeScanView(View):
    """
    Handle QR code scanning and route to appropriate page based on user type.
    
    Routes:
    - Doctor scanning their own QR: /doctor/{id}/ (profile page)
    - Vendor scanning QR: /vendor/transaction/new/?doctor_id={id}
    - Admin scanning QR: /admin/accounts/doctor/{id}/change/
    - Not authenticated: 404 page
    """
    
    def get(self, request, qr_code):
        # Find the doctor by QR code
        doctor = get_object_or_404(Doctor, qr_code=qr_code)
        
        # If not authenticated, return 404
        if not request.user.is_authenticated:
            return redirect('login')
        
        user = request.user
        
        # Route based on user type
        if user.is_superuser or user.is_staff:
            # Admin/Staff: redirect to admin panel doctor profile
            return redirect(f'/admin/accounts/doctor/{doctor.id}/change/')
        
        elif user.type == 'DOCTOR':
            # Doctor: check if it's their own profile
            if hasattr(user, 'doctor_profile') and user.doctor_profile == doctor:
                # Their own profile
                return redirect('doctor_profile', pk=doctor.id)
            else:
                # Someone else's profile - deny access
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("ليس لديك صلاحية لعرض هذا الملف.")
        
        elif user.type == 'VENDOR':
            # Vendor: redirect to transaction creation with doctor pre-filled
            return redirect(f'/vendor/transaction/new/?doctor_id={doctor.id}')
        
        # Fallback: 404
        raise Http404("صفحة غير موجودة")
