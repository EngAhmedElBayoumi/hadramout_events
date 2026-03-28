from django.urls import path
from .views import HomeView, VendorDashboardView, TransactionCreateView, DoctorLookupView, DoctorProfileView, CashierCreateView, CashierDeleteView, SendOTPView, AdminCompanyDelegatesView, AdminDelegateSpecialtiesView, VoucherTransferView
from .qr_views import QRCodeScanView
from .api_views import dashboard_stats_api
from accounts.views import DoctorRegistrationView, SpecialtySearchView, RegistrationQRView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('api/dashboard-stats/', dashboard_stats_api, name='dashboard_stats_api'),
    path('vendor/dashboard/', VendorDashboardView.as_view(), name='vendor_dashboard'),
    path('vendor/transaction/new/', TransactionCreateView.as_view(), name='transaction_create'),
    path('vendor/transaction/send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('api/doctor-lookup/', DoctorLookupView.as_view(), name='doctor_lookup'),
    path('api/admin/company-delegates/', AdminCompanyDelegatesView.as_view(), name='admin_company_delegates'),
    path('api/admin/delegate-specialties/', AdminDelegateSpecialtiesView.as_view(), name='admin_delegate_specialties'),
    path('doctor/<int:pk>/', DoctorProfileView.as_view(), name='doctor_profile'),
    path('voucher/<int:pk>/transfer/', VoucherTransferView.as_view(), name='voucher_transfer'),
    path('scan/<str:qr_code>/', QRCodeScanView.as_view(), name='qr_scan'),
    path('vendor/cashier/new/', CashierCreateView.as_view(), name='cashier_create'),
    path('vendor/cashier/<int:pk>/delete/', CashierDeleteView.as_view(), name='cashier_delete'),
    # Doctor registration
    path('register/doctor/', DoctorRegistrationView.as_view(), name='doctor_register'),
    path('api/specialties/', SpecialtySearchView.as_view(), name='specialty_search'),
    path('registration-qr/', RegistrationQRView.as_view(), name='registration_qr'),
]

