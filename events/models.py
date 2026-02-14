from django.db import models
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Event(models.Model):
    name = models.CharField(_('Name'), max_length=255)
    date = models.DateField(_('Date'))
    company = models.ForeignKey('core.PharmaceuticalCompany', on_delete=models.CASCADE, verbose_name=_('Company'))
    voucher_value = models.DecimalField(_('Voucher Value'), max_digits=10, decimal_places=2)
    voucher_expiry_days = models.IntegerField(_('Voucher Expiry Days'), default=90)
    doctors = models.ManyToManyField('accounts.Doctor', related_name='events', blank=True, verbose_name=_('Doctors'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Events')

    def __str__(self):
        return f"{self.name} - {self.date}"

class Voucher(models.Model):
    doctor = models.ForeignKey('accounts.Doctor', on_delete=models.CASCADE, related_name='vouchers', verbose_name=_('Doctor'))
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='vouchers', verbose_name=_('Event'))
    initial_value = models.DecimalField(_('Initial Value'), max_digits=10, decimal_places=2)
    current_balance = models.DecimalField(_('Current Balance'), max_digits=10, decimal_places=2)
    issue_date = models.DateField(_('Issue Date'), auto_now_add=True)
    expiry_date = models.DateField(_('Expiry Date'))
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Voucher')
        verbose_name_plural = _('Vouchers')

    def __str__(self):
        return f"Voucher for {self.doctor} - {self.event.name}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.expiry_date:
            # If creating new and no expiry date set, calculate it from event settings
            # Note: This logic might be better in the signal/logic layer, but good default here.
            # self.issue_date is auto_now_add, so it might be None before save.
            # We used auto_now_add=True, so logic needing strictly issue_date might need explicit set.
            # Let's rely on views/signals for precise date logic, but add a fallback here if needed.
            if self.event:
                 self.expiry_date = timezone.now().date() + timedelta(days=self.event.voucher_expiry_days)
        super().save(*args, **kwargs)
