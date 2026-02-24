from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Event, Voucher
from django.utils import timezone

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
@receiver(post_save, sender=Voucher)
def send_voucher_notification(sender, instance, created, **kwargs):
    if created:
        doctor = instance.doctor
        if not doctor.email:
            return

        # Determine company info
        company_name = "غير محددة"
        if instance.company:
            company_name = instance.company.name
        elif instance.event and instance.event.company:
            company_name = instance.event.company.name

        # Determine event info
        event_info = ""
        if instance.event:
            event_info = f"\nمن ندوة: {instance.event.name}"

        # Calculate validity duration
        validity_days = (instance.expiry_date - instance.issue_date).days
        
        subject = "تم إضافة قسيمة شراء جديدة - حضرموت ميت غمر"
        message = f"""
مرحباً د. {doctor.name}،

تم إضافة قسيمة شراء جديدة لسيادتكم ببيانات كالتالي:

- من شركة: {company_name}{event_info}
- بقيمة: {instance.initial_value} ج.م
- تاريخ انتهاء القسيمة: {instance.expiry_date}
- مدة صلاحية القسيمة: {validity_days} يوم

شكراً لاستخدامكم نظام حضرموت ميت غمر.
        """

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [doctor.email],
                fail_silently=True,
            )
        except Exception:
            pass
