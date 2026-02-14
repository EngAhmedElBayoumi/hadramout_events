from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import Event, Voucher

@receiver(m2m_changed, sender=Event.doctors.through)
def create_vouchers_for_doctors(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action == "post_add":
        # instance is the Event object
        # pk_set contains the primary keys of the added doctors
        for doctor_id in pk_set:
            # Check if voucher already exists to avoid duplicates
            if not Voucher.objects.filter(event=instance, doctor_id=doctor_id).exists():
                Voucher.objects.create(
                    event=instance,
                    doctor_id=doctor_id,
                    initial_value=instance.voucher_value,
                    current_balance=instance.voucher_value,
                    # expiry_date will be calculated by Voucher.save()
                )
