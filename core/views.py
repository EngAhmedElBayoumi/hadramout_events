from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, View, DetailView, CreateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from accounts.models import Doctor, Vendor, User, Delegate, Specialty
from core.models import Transaction, VendorSettlement
from core.services import process_transaction, generate_otp, send_otp_email, verify_otp
from events.models import Voucher, VoucherTransfer
from django.core.exceptions import ValidationError, PermissionDenied
from django.urls import reverse_lazy
from decimal import Decimal
import re
import uuid

class AdminCompanyDelegatesView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        company_id = request.GET.get('company_id')
        delegates = Delegate.objects.all().prefetch_related('companies')
        
        data = []
        for d in delegates:
            is_general = d.companies.count() == 0
            is_company = False
            if company_id and str(company_id).isdigit():
                is_company = d.companies.filter(id=company_id).exists()
            
            cat = 'من شركات أخرى'
            if is_company:
                cat = 'تابع للشركة'
            elif is_general:
                cat = 'عام (بدون شركة)'
                
            data.append({
                'id': d.id,
                'name': f"{d.name} [{cat}]",
                'is_company': is_company,
                'is_general': is_general
            })
            
        return JsonResponse({'delegates': data})

class AdminDelegateSpecialtiesView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        delegate_ids = request.GET.getlist('delegate_ids[]')
        if not delegate_ids:
            return JsonResponse({'specialty_ids': []})
            
        specialties = Specialty.objects.filter(delegates__id__in=delegate_ids).distinct()
        data = [s.id for s in specialties]
        return JsonResponse({'specialty_ids': data})

class AdminCompanyDelegatesView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        company_id = request.GET.get('company_id')
        term = request.GET.get('term', '')
        
        delegates = Delegate.objects.all().prefetch_related('companies')
        if term:
            delegates = delegates.filter(Q(name__icontains=term) | Q(phone__icontains=term))
            
        delegates = delegates[:50]
        
        company_delegates = []
        general_delegates = []
        other_delegates = []
        
        for d in delegates:
            is_general = d.companies.count() == 0
            is_company = False
            if company_id and str(company_id).isdigit():
                is_company = d.companies.filter(id=company_id).exists()
            
            item = {'id': str(d.id), 'text': d.name}
            
            if is_company:
                company_delegates.append(item)
            elif is_general:
                general_delegates.append(item)
            else:
                other_delegates.append(item)
                
        results = []
        if company_delegates:
            results.append({
                'text': 'تابع للشركة',
                'children': company_delegates
            })
        if general_delegates:
            results.append({
                'text': 'عام (بدون شركة)',
                'children': general_delegates
            })
        if other_delegates:
            results.append({
                'text': 'من شركات أخرى',
                'children': other_delegates
            })
            
        return JsonResponse({
            'results': results,
            'pagination': {'more': False}
        })

class AdminDelegateSpecialtiesView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        delegate_ids = request.GET.getlist('delegate_ids[]')
        if not delegate_ids:
            return JsonResponse({'specialties': []})
            
        specialties = Specialty.objects.filter(delegates__id__in=delegate_ids).distinct()
        data = [{'id': s.id, 'text': s.name} for s in specialties]
        return JsonResponse({'specialties': data})

class HomeView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        
        user = request.user
        if user.is_superuser or user.is_staff:
            return redirect('/admin/')
        elif user.type == 'VENDOR':
            vendor = getattr(user, 'vendor_profile', None)
            if vendor and vendor.role == 'CASHIER':
                return redirect('transaction_create')
            return redirect('vendor_dashboard')
        elif user.type == 'DOCTOR':
            doctor = getattr(user, 'doctor_profile', None)
            if doctor:
                return redirect('doctor_profile', pk=doctor.pk)
        
        return redirect('/admin/')

class VendorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.type == 'VENDOR' or user.is_superuser or user.is_staff)

class VendorAdminRequiredMixin(UserPassesTestMixin):
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

class VendorDashboardView(LoginRequiredMixin, VendorAdminRequiredMixin, TemplateView):
    template_name = 'core/vendor_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor = getattr(self.request.user, 'vendor_profile', None)
        
        if not vendor:
             raise PermissionDenied("لم يتم العثور على ملف بائع لهذا الحساب.")
        
        all_transactions = Transaction.objects.filter(vendor=vendor).order_by('-transaction_date')
        total_earned = all_transactions.aggregate(Sum('amount_spent'))['amount_spent__sum'] or Decimal('0.00')
        total_paid = VendorSettlement.objects.filter(vendor=vendor).aggregate(Sum('amount_settled'))['amount_settled__sum'] or Decimal('0.00')
        total_pending = total_earned - total_paid

        context['vendor'] = vendor
        context['total_sales'] = total_earned
        context['total_paid'] = total_paid
        context['total_pending'] = total_pending
        context['total_transactions'] = all_transactions.count()
        context['recent_transactions'] = all_transactions[:20]
        context['settlements'] = VendorSettlement.objects.filter(vendor=vendor).order_by('-settlement_date')[:10]
        
        return context

class SendOTPView(LoginRequiredMixin, VendorRequiredMixin, View):
    """View to generate and send OTP to doctor's email."""
    def post(self, request):
        doctor_id = request.POST.get('doctor_id')
        amount = request.POST.get('amount')
        
        if not doctor_id or not amount:
            return JsonResponse({'success': False, 'error': 'بيانات ناقصة.'}, status=400)
            
        try:
            doctor = Doctor.objects.get(id=doctor_id)
            vendor = request.user.vendor_profile
            
            otp = generate_otp()
            token = send_otp_email(doctor, otp, amount, vendor.name)
            if token:
                return JsonResponse({
                    'success': True, 
                    'message': f'تم إرسال رمز التأكيد إلى بريد الطبيب: {doctor.email}',
                    'transaction_token': token,
                    'doctor_email': doctor.email
                })
            else:
                return JsonResponse({'success': False, 'error': 'فشل إرسال البريد الإلكتروني. تأكد من إعدادات السيرفر.'}, status=500)
                
        except Doctor.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'طبيب غير موجود.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class TransactionCreateView(LoginRequiredMixin, VendorRequiredMixin, View):
    template_name = 'core/transaction_form.html'

    def get(self, request):
        vendor = getattr(request.user, 'vendor_profile', None)
        if not vendor:
            raise PermissionDenied("يجب أن يكون لديك ملف بائع لإجراء هذه العملية.")
        
        effective_vendor = vendor
        if vendor.role == 'CASHIER' and vendor.parent_vendor:
            effective_vendor = vendor.parent_vendor

        context = {
            'is_cashier': vendor.role == 'CASHIER',
            'vendor': vendor,
            'has_management_fee': effective_vendor.has_management_fee,
        }
        
        doctor_id = request.GET.get('doctor_id')
        if doctor_id:
            try:
                doctor = Doctor.objects.get(id=doctor_id)
                balance = doctor.vouchers.filter(is_active=True).aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal('0.00')
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
        token = request.POST.get('transaction_token')
        otp_code = request.POST.get('otp_code')

        vendor = getattr(request.user, 'vendor_profile', None)
        if not vendor:
            raise PermissionDenied("يجب أن يكون لديك ملف بائع لإجراء هذه العملية.")

        # Verify OTP first
        is_valid, result = verify_otp(token, otp_code)
        if not is_valid:
            error = result # Error message from verify_otp
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error}, status=400)
            messages.error(request, error)
            return self.get(request)

        # OTP is valid, result contains the stored data (doctor_id, amount)
        doctor_id = result['doctor_id']
        amount = result['amount']
        # Note: description is not in OTP data, we could add it or pass it separately
        description = request.POST.get('description', '')

        try:
            doctor = Doctor.objects.get(id=doctor_id)
            trx = process_transaction(vendor, doctor, amount, description, created_by=request.user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'invoice': {
                        'invoice_number': trx.invoice_number,
                        'doctor_name': doctor.name,
                        'vendor_name': trx.vendor.name,
                        'amount_spent': float(trx.amount_spent),
                        'management_fee': float(trx.management_fee_amount),
                        'total_deducted': float(trx.total_deducted),
                        'date': trx.transaction_date.strftime('%Y-%m-%d %H:%M'),
                        'description': trx.items_description,
                    }
                })
            
            messages.success(request, f"تمت العملية بنجاح! رقم الفاتورة: {trx.invoice_number}")
            if vendor.role == 'CASHIER':
                return redirect('transaction_create')
            return redirect('vendor_dashboard')
            
        except Doctor.DoesNotExist:
            error = "طبيب غير موجود."
        except ValidationError as e:
            error = e.messages[0] if hasattr(e, 'messages') else str(e)
            if "Insufficient balance" in error:
                match = re.search(r"Available: ([\d\.]+), Required: ([\d\.]+)", error)
                if match:
                    avail, req = match.groups()
                    error = f"عذراً، الرصيد المتاح غير كافٍ. المتاح: {avail} ج.م، المطلوب: {req} ج.م"
        except Exception as e:
            error = f"خطأ غير متوقع: {str(e)}"

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error}, status=400)
        
        messages.error(request, error)
        return self.get(request)

class DoctorLookupView(LoginRequiredMixin, VendorRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        vendor = getattr(request.user, 'vendor_profile', None)
        is_cashier = vendor and vendor.role == 'CASHIER'
        
        if is_cashier:
            # Cashier can only match exact ID or exact QR code payload
            if query.isdigit():
                doctors = Doctor.objects.filter(id=query)
            else:
                doctors = Doctor.objects.filter(qr_code__iexact=query)
        else:
            # Vendor Admin can search broadly
            if query.isdigit():
                doctors = Doctor.objects.filter(id=query)
            else:
                doctors = Doctor.objects.filter(phone__icontains=query) | Doctor.objects.filter(name__icontains=query) | Doctor.objects.filter(qr_code__iexact=query)
        
        results = []
        for doc in doctors[:5]:
            balance = doc.vouchers.filter(is_active=True).aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal('0.00')
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
        user = request.user
        doctor_to_view = self.get_object()
        
        if user.is_superuser or user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        
        if user.type == 'VENDOR':
            vendor = getattr(user, 'vendor_profile', None)
            if vendor and vendor.role == 'ADMIN':
                return super().dispatch(request, *args, **kwargs)
            raise PermissionDenied("ليس لديك صلاحية لعرض الملف الكامل للطبيب.")
        
        if user.type == 'DOCTOR':
            if hasattr(user, 'doctor_profile') and user.doctor_profile == doctor_to_view:
                return super().dispatch(request, *args, **kwargs)
        
        raise PermissionDenied("ليس لديك صلاحية لعرض هذا الملف.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vouchers = self.object.vouchers.all().order_by('-expiry_date')
        active_vouchers = vouchers.filter(is_active=True)
        
        context['vouchers'] = vouchers
        context['total_balance'] = active_vouchers.aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal('0.00')
        context['active_vouchers_count'] = active_vouchers.count()
        context['expired_vouchers_count'] = vouchers.filter(is_active=False).count()
        context['transactions'] = Transaction.objects.filter(doctor=self.object).order_by('-transaction_date')
        context['total_spent'] = Transaction.objects.filter(doctor=self.object).aggregate(
            total=Sum('total_deducted'))['total'] or Decimal('0.00')
        context['transfers_made'] = self.object.transfers_made.all().order_by('-transfer_date')
        return context

class VoucherTransferView(LoginRequiredMixin, View):
    def post(self, request, pk):
        voucher = get_object_or_404(Voucher, pk=pk)
        user = request.user
        
        # Ensure only the owning doctor can transfer
        if user.type != 'DOCTOR' or not hasattr(user, 'doctor_profile') or voucher.doctor != user.doctor_profile:
            messages.error(request, "لا تملك صلاحية تحويل هذه القسيمة.")
            # If they are not a doctor but somehow got here, redirect home.
            if hasattr(user, 'doctor_profile'):
                return redirect('doctor_profile', pk=user.doctor_profile.pk)
            return redirect('home')

        if not voucher.is_active:
            messages.error(request, "لا يمكن تحويل قسيمة غير نشطة.")
            return redirect('doctor_profile', pk=user.doctor_profile.pk)

        target_search = request.POST.get('target_search', '').strip()
        if not target_search:
            messages.error(request, "يرجى توفير رقم هاتف أو كود الطبيب المحول إليه.")
            return redirect('doctor_profile', pk=user.doctor_profile.pk)

        # Allow searching by phone or qr_code
        target_doctor = Doctor.objects.filter(
            Q(phone=target_search) | Q(qr_code__iexact=target_search)
        ).first()

        if not target_doctor:
            messages.error(request, "لم يتم العثور على طبيب بهذا الرقم أو الكود.")
            return redirect('doctor_profile', pk=user.doctor_profile.pk)

        if target_doctor == voucher.doctor:
            messages.error(request, "لا يمكنك تحويل القسيمة لنفسك.")
            return redirect('doctor_profile', pk=user.doctor_profile.pk)

        old_doctor = voucher.doctor
        old_doctor_name = old_doctor.name
        
        # Perform transfer
        voucher.doctor = target_doctor
        transfer_note = f"تم التحويل من د. {old_doctor_name}"
        if voucher.notes:
            voucher.notes += f"\n{transfer_note}"
        else:
            voucher.notes = transfer_note
        voucher.save()

        # Log transfer history
        VoucherTransfer.objects.create(
            from_doctor=old_doctor,
            to_doctor=target_doctor,
            voucher=voucher
        )

        messages.success(request, f"تم تحويل القسيمة بنجاح إلى د. {target_doctor.name}.")
        return redirect('doctor_profile', pk=user.doctor_profile.pk)

class CashierCreateView(LoginRequiredMixin, VendorAdminRequiredMixin, CreateView):
    model = User
    template_name = 'core/cashier_form.html'
    fields = ['username', 'password', 'first_name', 'last_name', 'email']
    success_url = reverse_lazy('vendor_dashboard')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.type = 'VENDOR'
        user.set_password(form.cleaned_data['password'])
        user.save()
        
        parent_vendor = self.request.user.vendor_profile
        Vendor.objects.create(
            user=user,
            name=f"{user.first_name} {user.last_name}" or user.username,
            parent_vendor=parent_vendor,
            role='CASHIER',
            phone=self.request.POST.get('phone', ''),
            email=user.email
        )
        messages.success(self.request, "تم إنشاء حساب الكاشير بنجاح.")
        return redirect(self.success_url)

class CashierDeleteView(LoginRequiredMixin, VendorAdminRequiredMixin, View):
    def post(self, request, pk):
        parent_vendor = request.user.vendor_profile
        cashier_vendor = get_object_or_404(Vendor, id=pk, parent_vendor=parent_vendor, role='CASHIER')
        user = cashier_vendor.user
        cashier_vendor.delete()
        user.delete()
        messages.success(request, "تم حذف حساب الكاشير بنجاح.")
        return redirect('vendor_dashboard')
