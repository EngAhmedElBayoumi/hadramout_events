from django.urls import path
from .views import HomeView, VendorDashboardView, TransactionCreateView, DoctorLookupView, DoctorProfileView
from .api_views import dashboard_stats_api

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('api/dashboard-stats/', dashboard_stats_api, name='dashboard_stats_api'),
    path('vendor/dashboard/', VendorDashboardView.as_view(), name='vendor_dashboard'),
    path('vendor/transaction/new/', TransactionCreateView.as_view(), name='transaction_create'),
    path('api/doctor-lookup/', DoctorLookupView.as_view(), name='doctor_lookup'),
    path('doctor/<int:pk>/', DoctorProfileView.as_view(), name='doctor_profile'),
]
