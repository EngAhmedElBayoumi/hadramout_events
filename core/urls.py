from django.urls import path
from .views import HomeView, VendorDashboardView, TransactionCreateView, DoctorLookupView, DoctorProfileView, VerifyOTPView, ResendOTPView
from .qr_views import QRCodeScanView
from .api_views import dashboard_stats_api
from accounts.views import DoctorRegistrationView, SpecialtySearchView, RegistrationQRView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('api/dashboard-stats/', dashboard_stats_api, name='dashboard_stats_api'),
    path('vendor/dashboard/', VendorDashboardView.as_view(), name='vendor_dashboard'),
    path('vendor/transaction/new/', TransactionCreateView.as_view(), name='transaction_create'),
    path('api/doctor-lookup/', DoctorLookupView.as_view(), name='doctor_lookup'),
    path('api/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('api/resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    path('doctor/<int:pk>/', DoctorProfileView.as_view(), name='doctor_profile'),
    path('scan/<str:qr_code>/', QRCodeScanView.as_view(), name='qr_scan'),
    # Doctor registration
    path('register/doctor/', DoctorRegistrationView.as_view(), name='doctor_register'),
    path('api/specialties/', SpecialtySearchView.as_view(), name='specialty_search'),
    path('registration-qr/', RegistrationQRView.as_view(), name='registration_qr'),
]

