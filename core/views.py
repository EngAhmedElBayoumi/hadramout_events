from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, View, DetailView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from accounts.models import Doctor, Vendor
from core.models import Transaction
from core.services import process_transaction
from events.models import Voucher
from django.core.exceptions import ValidationError
from decimal import Decimal

class HomeView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        
        user = request.user
        if user.is_superuser or user.is_staff:
            return redirect('/admin/')
        elif user.type == 'VENDOR':
            return redirect('vendor_dashboard')
        elif user.type == 'DOCTOR':
            # Redirect to their own profile if they are a doctor
            doctor = getattr(user, 'doctor_profile', None)
            if doctor:
                return redirect('doctor_profile', pk=doctor.pk)
        
        # Fallback for generic users
        return redirect('/admin/')

class VendorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.type == 'VENDOR' or user.is_superuser or user.is_staff)

class VendorAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only Vendor Admins can access (not Cashiers)"""
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        if user.type == 'VENDOR':
            vendor = getattr(user, 'vendor_profile', None)
            if vendor and vendor.role == 'ADMIN':
                return True
        return False

from core.models import Transaction, VendorSettlement

class VendorDashboardView(LoginRequiredMixin, VendorRequiredMixin, TemplateView):
    template_name = 'core/vendor_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor = getattr(self.request.user, 'vendor_profile', None)
        if not vendor:
            vendor = Vendor.objects.first()
        context['vendor'] = vendor
        
        # Financial Summary
        # 1. Total Earnings (Sum of amount_spent in all transactions)
        total_earned = Transaction.objects.filter(vendor=vendor).aggregate(Sum('amount_spent'))['amount_spent__sum'] or Decimal('0.00')
        
        # 2. Total Paid (Sum of amount_settled in settlements)
        total_paid = VendorSettlement.objects.filter(vendor=vendor).aggregate(Sum('amount_settled'))['amount_settled__sum'] or Decimal('0.00')
        
        # 3. Pending Balance
        total_pending = total_earned - total_paid

        context['total_sales'] = total_earned
        context['total_paid'] = total_paid
        context['total_pending'] = total_pending
        context['total_transactions'] = Transaction.objects.filter(vendor=vendor).count()
        
        # Histories
        context['recent_transactions'] = Transaction.objects.filter(vendor=vendor).order_by('-transaction_date')[:10]
        context['settlements'] = VendorSettlement.objects.filter(vendor=vendor).order_by('-settlement_date')[:10]
        
        return context

class TransactionCreateView(LoginRequiredMixin, VendorRequiredMixin, View):
    template_name = 'core/transaction_form.html'

    def get(self, request):
        context = {}
        # Check if user is a Vendor Cashier
        vendor = getattr(request.user, 'vendor_profile', None)
        if not vendor:
            vendor = Vendor.objects.first()
        
        is_cashier = vendor and vendor.role == 'CASHIER'
        context['is_cashier'] = is_cashier
        context['vendor'] = vendor
        context['has_management_fee'] = vendor.has_management_fee if vendor else True
        
        # Support pre-filling doctor from QR scan (URL param: ?doctor_id=X)
        doctor_id = request.GET.get('doctor_id')
        if doctor_id:
            try:
                doctor = Doctor.objects.get(id=doctor_id)
                active_vouchers = doctor.vouchers.filter(is_active=True)
                balance = sum(v.current_balance for v in active_vouchers)
                context['prefill_doctor'] = {
                    'id': doctor.id,
                    'name': doctor.name,
                    'phone': doctor.phone,
                    'balance': float(balance),
                }
            except Doctor.DoesNotExist:
                pass
        return render(request, self.template_name, context)

    def post(self, request):
        doctor_id = request.POST.get('doctor_id')
        amount = request.POST.get('amount')
        description = request.POST.get('description', '')

        try:
            vendor = getattr(request.user, 'vendor_profile', None)
            if not vendor:
                vendor = Vendor.objects.first()
            doctor = Doctor.objects.get(id=doctor_id)
            
            trx = process_transaction(vendor, doctor, amount, description, created_by=request.user)
            # Return JSON for AJAX-based submission (invoice printing)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'invoice': {
                        'invoice_number': trx.invoice_number,
                        'doctor_name': doctor.name,
                        'vendor_name': vendor.name,
                        'amount_spent': float(trx.amount_spent),
                        'management_fee': float(trx.management_fee_amount),
                        'total_deducted': float(trx.total_deducted),
                        'date': trx.transaction_date.strftime('%Y-%m-%d %H:%M'),
                        'description': trx.items_description,
                    }
                })
            messages.success(request, f"تمت العملية بنجاح! رقم الفاتورة: {trx.invoice_number}")
            return redirect('vendor_dashboard')
            
        except Doctor.DoesNotExist:
            error = "طبيب غير موجود."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error}, status=400)
            messages.error(request, error)
        except ValidationError as e:
            # Handle Django ValidationError to pull message out of list
            error = e.messages[0] if hasattr(e, 'messages') else str(e)
            if "Insufficient balance" in error:
                # Custom Arabic message for balance errors
                import re
                match = re.search(r"Available: ([\d\.]+), Required: ([\d\.]+)", error)
                if match:
                    avail, req = match.groups()
                    error = f"عذراً، الرصيد المتاح غير كافٍ. المتاح: {avail} ج.م، المطلوب: {req} ج.م"
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error}, status=400)
            messages.error(request, error)
        except Exception as e:
            error = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error}, status=400)
            messages.error(request, f"خطأ غير متوقع: {e}")
        
        return render(request, self.template_name)

class DoctorLookupView(LoginRequiredMixin, VendorAdminRequiredMixin, View):
    """Search for doctors - only available to Vendor Admins, not Cashiers"""
    def get(self, request):
        query = request.GET.get('q', '')
        if query.isdigit():
            doctors = Doctor.objects.filter(id=query)
        else:
            doctors = Doctor.objects.filter(phone__icontains=query) | Doctor.objects.filter(name__icontains=query) | Doctor.objects.filter(qr_code__iexact=query)
        
        results = []
        for doc in doctors[:5]:
            active_vouchers = doc.vouchers.filter(is_active=True)
            balance = sum(v.current_balance for v in active_vouchers)
            results.append({
                'id': doc.id,
                'name': doc.name,
                'phone': doc.phone,
                'specialty': doc.specialty.name if doc.specialty else '',
                'balance': float(balance)
            })
        return JsonResponse({'results': results})


class DoctorProfileView(LoginRequiredMixin, DetailView):
    model = Doctor
    template_name = 'core/doctor_profile.html'
    context_object_name = 'doctor'

    def dispatch(self, request, *args, **kwargs):
        # Security Check: Ensure a doctor can only see their own profile
        user = request.user
        doctor_to_view = self.get_object()
        
        # Admins, Staff, and Vendors can see any profile (for verification/scanning)
        if user.is_superuser or user.is_staff or user.type == 'VENDOR':
            return super().dispatch(request, *args, **kwargs)
        
        # Doctors can ONLY see their own profile
        if user.type == 'DOCTOR':
            if hasattr(user, 'doctor_profile') and user.doctor_profile == doctor_to_view:
                return super().dispatch(request, *args, **kwargs)
        
        # Deny access for everyone else
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("ليس لديك صلاحية لعرض هذا الملف.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vouchers = self.object.vouchers.all().order_by('-expiry_date')
        context['vouchers'] = vouchers
        # Total active balance
        active_vouchers = vouchers.filter(is_active=True)
        context['total_balance'] = sum(v.current_balance for v in active_vouchers)
        context['active_vouchers_count'] = active_vouchers.count()
        context['expired_vouchers_count'] = vouchers.filter(is_active=False).count()
        context['transactions'] = Transaction.objects.filter(doctor=self.object).order_by('-transaction_date')
        context['total_spent'] = Transaction.objects.filter(doctor=self.object).aggregate(
            total=Sum('total_deducted'))['total'] or 0
        return context
