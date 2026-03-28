from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from decimal import Decimal
from accounts.models import Vendor, Doctor
from events.models import Voucher
from .models import Transaction
import random
import string

def generate_otp():
    """Generates a 6-digit numeric OTP."""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(doctor, otp, amount, vendor_name):
    """Sends OTP to doctor's email and stores it in cache with a unique token."""
    import uuid
    transaction_token = str(uuid.uuid4())
    subject = "رمز تأكيد عملية الخصم - قرية حضرموت"
    message = f"""
    مرحباً دكتور {doctor.name}،
    
    هناك محاولة لخصم مبلغ {amount} ج.م من قسائمك في {vendor_name}.
    رمز التأكيد الخاص بك هو: {otp}
    
    يرجى تزويد التاجر بهذا الرمز لإتمام العملية. إذا لم تكن أنت من يقوم بهذه العملية، يرجى تجاهل هذه الرسالة.
    يرجى العلم أن هذا الرمز صالح لمدة 10 دقائق فقط وبحد أقصى 5 محاولات.
    
    شكراً لتعاملكم معنا.
    """
    
    # Store OTP data in cache
    cache_data = {
        'otp': otp,
        'doctor_id': doctor.id,
        'amount': amount,
        'attempts': 0
    }
    cache.set(f"otp_token_{transaction_token}", cache_data, timeout=600)
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [doctor.email],
            fail_silently=False,
        )
        return transaction_token
    except Exception:
        return None

def verify_otp(token, input_otp):
    """Verifies OTP and tracks failed attempts."""
    cache_key = f"otp_token_{token}"
    data = cache.get(cache_key)
    
    if not data:
        return False, "انتهت صلاحية الرمز أو أنه غير صالح."
        
    if data['attempts'] >= 5:
        cache.delete(cache_key)
        return False, "لقد تجاوزت الحد الأقصى للمحاولات (5). يرجى طلب رمز جديد."
        
    if data['otp'] == input_otp:
        return True, data
        
    # Increment attempts
    data['attempts'] += 1
    cache.set(cache_key, data, timeout=600)
    
    remaining = 5 - data['attempts']
    if remaining > 0:
        return False, f"رمز غير صحيح. متبقي لديك {remaining} محاولات."
    else:
        cache.delete(cache_key)
        return False, "لقد تجاوزت الحد الأقصى للمحاولات. يرجى طلب رمز جديد."

def process_transaction(vendor, doctor, amount_spent, items_description="", created_by=None):
    """
    Processes a transaction for a doctor at a vendor.
    Deducts the total amount (spent + fee) from the doctor's active vouchers.
    """
    amount_spent = Decimal(amount_spent)
    
    # Use parent vendor's settings if this is a cashier
    effective_vendor = vendor
    if vendor.role == 'CASHIER' and vendor.parent_vendor:
        effective_vendor = vendor.parent_vendor

    # Check if vendor has management fee enabled
    management_fee_percentage = Decimal("0.25") if effective_vendor.has_management_fee else Decimal("0.00")
    management_fee_amount = amount_spent * management_fee_percentage
    total_deducted = amount_spent + management_fee_amount

    # Get active vouchers
    active_vouchers = Voucher.objects.filter(
        doctor=doctor, 
        is_active=True, 
        current_balance__gt=0
    ).order_by('expiry_date')

    total_balance = sum(v.current_balance for v in active_vouchers)

    if total_balance < total_deducted:
        raise ValidationError(f"Insufficient balance. Available: {total_balance}, Required: {total_deducted}")

    remaining_to_deduct = total_deducted
    used_vouchers = []
    
    with transaction.atomic():
        for voucher in active_vouchers:
            if remaining_to_deduct <= 0:
                break
            
            used_vouchers.append(voucher)

            if voucher.current_balance >= remaining_to_deduct:
                voucher.current_balance -= remaining_to_deduct
                remaining_to_deduct = 0
                if voucher.current_balance == 0:
                    voucher.is_active = False
            else:
                deduction = voucher.current_balance
                remaining_to_deduct -= deduction
                voucher.current_balance = 0
                voucher.is_active = False
            
            voucher.save()

        # Create Transaction record
        import uuid
        trx = Transaction.objects.create(
            vendor=effective_vendor,
            doctor=doctor,
            created_by=created_by,
            amount_spent=amount_spent,
            management_fee_percentage=management_fee_percentage * 100,
            management_fee_amount=management_fee_amount,
            total_deducted=total_deducted,
            items_description=items_description,
            invoice_number=str(uuid.uuid4())
        )
        trx.vouchers.set(used_vouchers)
        
        # Clear OTP from cache after successful transaction
        cache.delete(f"otp_token_{created_by.id if created_by else 'anon'}") # This was a cleanup placeholder, actual cleanup is by token
        
        return trx
