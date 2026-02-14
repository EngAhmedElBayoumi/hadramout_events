from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, View
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from accounts.models import Doctor, Vendor
from core.models import Transaction
from core.services import process_transaction
from events.models import Voucher
from decimal import Decimal

class VendorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.type == 'VENDOR'

class VendorDashboardView(LoginRequiredMixin, VendorRequiredMixin, TemplateView):
    template_name = 'core/vendor_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor = self.request.user.vendor_profile
        context['vendor'] = vendor
        context['recent_transactions'] = Transaction.objects.filter(vendor=vendor).order_by('-transaction_date')[:10]
        context['total_sales'] = Transaction.objects.filter(vendor=vendor).aggregate(Sum('amount_spent'))['amount_spent__sum'] or 0
        return context

class TransactionCreateView(LoginRequiredMixin, VendorRequiredMixin, View):
    template_name = 'core/transaction_form.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        doctor_id = request.POST.get('doctor_id')
        amount = request.POST.get('amount')
        description = request.POST.get('description', '')

        try:
            vendor = request.user.vendor_profile
            doctor = Doctor.objects.get(id=doctor_id)
            
            trx = process_transaction(vendor, doctor, amount, description)
            messages.success(request, f"تمت العملية بنجاح! رقم الفاتورة: {trx.invoice_number}")
            return redirect('vendor_dashboard')
            
        except Doctor.DoesNotExist:
            messages.error(request, "طبيب غير موجود.")
        except Exception as e:
            messages.error(request, f"خطأ: {e}")
        
        return render(request, self.template_name)

class DoctorLookupView(LoginRequiredMixin, VendorRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        doctors = Doctor.objects.filter(phone__icontains=query) | Doctor.objects.filter(name__icontains=query)
        results = []
        for doc in doctors[:5]:
            # Calculate balance
            active_vouchers = doc.vouchers.filter(is_active=True)
            balance = sum(v.current_balance for v in active_vouchers)
            results.append({
                'id': doc.id,
                'name': doc.name,
                'phone': doc.phone,
                'balance': balance
            })
from django.views.generic import DetailView

class DoctorProfileView(DetailView):
    model = Doctor
    template_name = 'core/doctor_profile.html'
    context_object_name = 'doctor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vouchers'] = self.object.vouchers.all().order_by('-expiry_date')
        # Transactions: logic to find transactions for this doctor
        context['transactions'] = Transaction.objects.filter(doctor=self.object).order_by('-transaction_date')
        return context
