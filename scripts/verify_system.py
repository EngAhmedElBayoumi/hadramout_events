import os
import django
from datetime import date

# Setup Django environment implementation (handled by shell, but good for standalone)
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
# django.setup()

from accounts.models import User, Doctor, Vendor
from core.models import PharmaceuticalCompany, Transaction
from core.services import process_transaction
from events.models import Event, Voucher

print("--- Starting Verification ---")

# 1. Setup Data
print("Creating Users...")
# Use get_or_create to avoid dupes if re-run
doc_user, _ = User.objects.get_or_create(username='doc1', defaults={'type': 'DOCTOR'})
ven_user, _ = User.objects.get_or_create(username='ven1', defaults={'type': 'VENDOR'})

doctor, _ = Doctor.objects.get_or_create(
    user=doc_user,
    defaults={'name': 'Dr. Test', 'phone': '01000000001', 'email': 'doc@test.com', 'specialty': 'Cardio'}
)
vendor, _ = Vendor.objects.get_or_create(
    user=ven_user,
    defaults={'name': 'Vendor Test', 'contact_person': 'Mr. V', 'phone': '01200000001', 'email': 'ven@test.com', 'address': 'Cairo', 'category': 'Supermarket'}
)

company, _ = PharmaceuticalCompany.objects.get_or_create(
    name='Pharma Corp',
    defaults={'contact_person': 'Rep 1', 'phone': '123', 'email': 'pharma@test.com', 'address': 'Giza'}
)

print("Creating Event...")
event, created = Event.objects.get_or_create(
    name='Launch Party',
    defaults={
        'date': date.today(),
        'company': company,
        'voucher_value': 1000.00,
        'voucher_expiry_days': 30
    }
)

# 2. Test Voucher Creation (Signal)
print("Adding Doctor to Event (Testing Signal)...")
# Clear previous vouchers for clean test if re-running
# Voucher.objects.all().delete() 
event.doctors.add(doctor)

voucher = Voucher.objects.filter(event=event, doctor=doctor).first()
if voucher:
    print(f"PASS: Voucher Created. Balance: {voucher.current_balance}")
else:
    print("FAIL: Voucher NOT Created")
    exit(1)

# 3. Test Transaction Logic
print("Processing Transaction...")
initial_balance = voucher.current_balance
amount_to_spend = 200.00
# Expected: 200 deduct + 50 fee = 250 total deduction.

try:
    trx = process_transaction(vendor, doctor, amount_to_spend, "Test Purchase")
    print(f"Transaction Created: {trx.invoice_number}")
    print(f"Amount Spent: {trx.amount_spent}, Fee: {trx.management_fee_amount}, Total: {trx.total_deducted}")
    
    # Reload voucher
    voucher.refresh_from_db()
    print(f"New Voucher Balance: {voucher.current_balance}")
    
    expected_balance = initial_balance - trx.total_deducted
    if voucher.current_balance == expected_balance:
        print("PASS: Balance updated correctly.")
    else:
        print(f"FAIL: Balance incorrect. Expected {expected_balance}, Got {voucher.current_balance}")

except Exception as e:
    print(f"FAIL: Transaction failed with error: {e}")

print("--- Verification Complete ---")
