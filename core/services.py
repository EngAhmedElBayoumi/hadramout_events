from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from accounts.models import Vendor, Doctor
from events.models import Voucher
from .models import Transaction

def process_transaction(vendor, doctor, amount_spent, items_description="", created_by=None):
    """
    Processes a transaction for a doctor at a vendor.
    Deducts the total amount (spent + fee) from the doctor's active vouchers
    starting with the one expiring soonest (FIFO).
    
    Args:
        vendor: Vendor instance
        doctor: Doctor instance
        amount_spent: Amount spent
        items_description: Description of items purchased
        created_by: User who created this transaction (for audit trail)
    """
    amount_spent = Decimal(amount_spent)
    
    # Check if vendor has management fee enabled
    if vendor.has_management_fee:
        management_fee_percentage = Decimal("0.25")
    else:
        management_fee_percentage = Decimal("0.00")
        
    management_fee_amount = amount_spent * management_fee_percentage
    total_deducted = amount_spent + management_fee_amount

    # Get active vouchers for the doctor, ordered by expiry date (FIFO)
    active_vouchers = Voucher.objects.filter(
        doctor=doctor, 
        is_active=True, 
        current_balance__gt=0
    ).order_by('expiry_date')

    # Calculate total available balance
    total_balance = sum(v.current_balance for v in active_vouchers)

    if total_balance < total_deducted:
        raise ValidationError(f"Insufficient balance. Available: {total_balance}, Required: {total_deducted}")

    # Start deducting
    remaining_to_deduct = total_deducted
    # We will need to associate the transaction with one main voucher for history,
    # or handle the split. The model has a single `voucher` FK. 
    # This is a limitation in the current model if a transaction spans multiple vouchers.
    # The spec says: "record... voucher (or vouchers from which deduction occurred)".
    # The current model `Transaction` has `voucher = ForeignKey`. 
    # Ideally, it should be ManyToMany or we create multiple transactions?
    # Or just link to the *primary* voucher (e.g. the first one)?
    # Or change `Transaction` model to M2M?
    # Spec row 23: `voucher` (FK to Voucher).
    # Spec row 60: "record ... voucher (or vouchers)". implying potential plural.
    # Given strict schema in row 23 (`ForeignKey`), I will link to the *first* voucher used.
    # If correct modeling was M2M, I'd change it. But for now I'll stick to schema 
    # and maybe add a note or link to the first one. 
    # A better approach for strict auditing is that a Transaction is linked to *one* voucher.
    # If a purchase exceeds one voucher, it should be split into multiple sub-transactions?
    # Or `Transaction` should have M2M `vouchers`.
    # I'll stick to linking the first one for now as the "primary" source, 
    # but strictly deducting from all.
    # Actually, let's look at the `Transaction` model I built.
    # `voucher = models.ForeignKey`.
    # I will link to the *first* voucher that covers the bulk or the first in FIFO.
    
    first_voucher = None
    
    with transaction.atomic():
        for voucher in active_vouchers:
            if remaining_to_deduct <= 0:
                break
            
            if not first_voucher:
                first_voucher = voucher

            if voucher.current_balance >= remaining_to_deduct:
                # This voucher covers the rest
                voucher.current_balance -= remaining_to_deduct
                remaining_to_deduct = 0
                if voucher.current_balance == 0:
                    voucher.is_active = False # Optional: deactivate if 0? Spec says yes.
            else:
                # Voucher is drained, need more
                deduction = voucher.current_balance
                remaining_to_deduct -= deduction
                voucher.current_balance = 0
                voucher.is_active = False
            
            voucher.save()

        # Create Transaction record
        import uuid
        trx = Transaction.objects.create(
            voucher=first_voucher, # Linking the first participating voucher
            vendor=vendor,
            doctor=doctor,
            created_by=created_by,
            amount_spent=amount_spent,
            management_fee_percentage=management_fee_percentage * 100, # Store as percentage (25.00)
            management_fee_amount=management_fee_amount,
            total_deducted=total_deducted,
            items_description=items_description,
            invoice_number=str(uuid.uuid4())
        )
        return trx
