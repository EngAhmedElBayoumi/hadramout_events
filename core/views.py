from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, View, DetailView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from accounts.models import Doctor, Vendor
from core.models import Transaction, TransactionOTP
from core.services import process_transaction
from events.models import Voucher
from django.core.exceptions import ValidationError
from decimal import Decimal
import random
import string

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
            
            # Validate amount
            amount_decimal = Decimal(amount)
            if amount_decimal <= 0:
                raise ValidationError("المبلغ يجب أن يكون أكبر من صفر")

            # Pre-validate balance before generating OTP
            if vendor.has_management_fee:
                fee = amount_decimal * Decimal("0.25")
            else:
                fee = Decimal("0.00")
            total_needed = amount_decimal + fee
            
            active_vouchers = Voucher.objects.filter(doctor=doctor, is_active=True, current_balance__gt=0)
            total_balance = sum(v.current_balance for v in active_vouchers)
            
            if total_balance < total_needed:
                avail = f"{total_balance:.2f}"
                req = f"{total_needed:.2f}"
                raise ValidationError(f"عذراً، الرصيد المتاح غير كافٍ. المتاح: {avail} ج.م، المطلوب: {req} ج.م")

            # Check if doctor has an email
            if not doctor.user.email:
                raise ValidationError("لا يوجد بريد إلكتروني مسجل لهذا الطبيب. لا يمكن إرسال رمز التحقق.")

            # Generate 6-digit OTP
            otp_code = ''.join(random.choices(string.digits, k=6))
            
            # Create OTP record
            otp = TransactionOTP.objects.create(
                doctor=doctor,
                vendor=vendor,
                created_by=request.user,
                otp_code=otp_code,
                amount=amount_decimal,
                description=description,
                expires_at=timezone.now() + timezone.timedelta(minutes=5),
            )

            # Send OTP via email
            try:
                send_mail(
                    'رمز التحقق من عملية الشراء - حضرموت',
                    f'مرحباً د. {doctor.name}،\n\n'
                    f'رمز التحقق من عملية الشراء الخاصة بك هو:\n\n'
                    f'🔑  {otp_code}\n\n'
                    f'المبلغ: {amount_decimal:.2f} ج.م\n'
                    f'التاجر: {vendor.name}\n\n'
                    f'هذا الرمز صالح لمدة 5 دقائق فقط.\n\n'
                    f'إذا لم تقم بهذه العملية، يرجى تجاهل هذه الرسالة.',
                    settings.DEFAULT_FROM_EMAIL,
                    [doctor.user.email],
                    fail_silently=False,
                )
                print("OTP sent successfully to", doctor.user.email)
            except Exception as e:
                # If email fails, still allow the transaction but log the error
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send OTP email to {doctor.user.email}: {e}")

            # Return OTP required response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'otp_required': True,
                    'transaction_token': str(otp.transaction_token),
                    'doctor_email': doctor.user.email[:3] + '***' + doctor.user.email[doctor.user.email.index('@'):],  # Masked email
                })
            
            messages.info(request, "تم إرسال رمز التحقق إلى بريد الطبيب الإلكتروني")
            return redirect('transaction_create')
            
        except Doctor.DoesNotExist:
            error = "طبيب غير موجود."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error}, status=400)
            messages.error(request, error)
        except ValidationError as e:
            error = e.messages[0] if hasattr(e, 'messages') else str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error}, status=400)
            messages.error(request, error)
        except Exception as e:
            error = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error}, status=400)
            messages.error(request, f"خطأ غير متوقع: {e}")
        
        return render(request, self.template_name)


class VerifyOTPView(LoginRequiredMixin, VendorRequiredMixin, View):
    """Verify OTP and process the transaction."""

    def post(self, request):
        transaction_token = request.POST.get('transaction_token')
        otp_code = request.POST.get('otp_code')

        try:
            otp = TransactionOTP.objects.get(transaction_token=transaction_token)
        except (TransactionOTP.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'error': 'رمز المعاملة غير صالح.'}, status=400)

        # Validate OTP
        if otp.is_used:
            return JsonResponse({'success': False, 'error': 'تم استخدام رمز التحقق هذا بالفعل.'}, status=400)

        if otp.is_expired:
            return JsonResponse({'success': False, 'error': 'انتهت صلاحية رمز التحقق. يرجى إعادة المحاولة.'}, status=400)

        if otp.otp_code != otp_code:
            return JsonResponse({'success': False, 'error': 'رمز التحقق غير صحيح.'}, status=400)

        # OTP is valid - process the transaction
        try:
            trx = process_transaction(
                otp.vendor,
                otp.doctor,
                str(otp.amount),
                otp.description,
                created_by=otp.created_by,
            )

            # Mark OTP as used
            otp.is_used = True
            otp.save()

            return JsonResponse({
                'success': True,
                'invoice': {
                    'invoice_number': trx.invoice_number,
                    'doctor_name': otp.doctor.name,
                    'vendor_name': otp.vendor.name,
                    'amount_spent': float(trx.amount_spent),
                    'management_fee': float(trx.management_fee_amount),
                    'total_deducted': float(trx.total_deducted),
                    'date': trx.transaction_date.strftime('%Y-%m-%d %H:%M'),
                    'description': trx.items_description,
                }
            })

        except ValidationError as e:
            error = e.messages[0] if hasattr(e, 'messages') else str(e)
            if "Insufficient balance" in error:
                import re
                match = re.search(r"Available: ([\d\.]+), Required: ([\d\.]+)", error)
                if match:
                    avail, req = match.groups()
                    error = f"عذراً، الرصيد المتاح غير كافٍ. المتاح: {avail} ج.م، المطلوب: {req} ج.م"
            return JsonResponse({'success': False, 'error': error}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class ResendOTPView(LoginRequiredMixin, VendorRequiredMixin, View):
    """Resend OTP for a pending transaction."""

    def post(self, request):
        transaction_token = request.POST.get('transaction_token')

        try:
            otp = TransactionOTP.objects.get(transaction_token=transaction_token)
        except (TransactionOTP.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'error': 'رمز المعاملة غير صالح.'}, status=400)

        if otp.is_used:
            return JsonResponse({'success': False, 'error': 'تم استخدام هذا الرمز بالفعل.'}, status=400)

        # Generate new OTP and extend expiry
        new_otp_code = ''.join(random.choices(string.digits, k=6))
        otp.otp_code = new_otp_code
        otp.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        otp.save()

        # Send new OTP email
        try:
            send_mail(
                'رمز التحقق الجديد - حضرموت',
                f'مرحباً د. {otp.doctor.name}،\n\n'
                f'رمز التحقق الجديد من عملية الشراء الخاصة بك هو:\n\n'
                f'🔑  {new_otp_code}\n\n'
                f'المبلغ: {otp.amount:.2f} ج.م\n'
                f'التاجر: {otp.vendor.name}\n\n'
                f'هذا الرمز صالح لمدة 5 دقائق فقط.',
                settings.DEFAULT_FROM_EMAIL,
                [otp.doctor.user.email],
                fail_silently=False,
            )
        except Exception:
            pass

        masked_email = otp.doctor.user.email[:3] + '***' + otp.doctor.user.email[otp.doctor.user.email.index('@'):]
        return JsonResponse({
            'success': True,
            'message': f'تم إرسال رمز تحقق جديد إلى {masked_email}',
        })


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
