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
    delegates = models.ManyToManyField('accounts.Delegate', related_name='events', blank=True, verbose_name=_('Delegates'))
    specialties = models.ManyToManyField('accounts.Specialty', related_name='events', blank=True, verbose_name=_('Specialties'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Events')

    def __str__(self):
        return f"{self.name} - {self.date}"

class Voucher(models.Model):
    doctor = models.ForeignKey('accounts.Doctor', on_delete=models.CASCADE, related_name='vouchers', verbose_name=_('Doctor'))
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='vouchers', verbose_name=_('Event'), null=True, blank=True)
    company = models.ForeignKey('core.PharmaceuticalCompany', on_delete=models.SET_NULL, verbose_name=_('Company'), null=True, blank=True)
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
        if self.event:
            return f"Voucher for {self.doctor} - {self.event.name}"
        else:
            return f"Voucher for {self.doctor}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.expiry_date:
            if self.event:
                 self.expiry_date = timezone.now().date() + timedelta(days=self.event.voucher_expiry_days)
            else:
                 # Default expiry for custom vouchers if no event is specified
                 self.expiry_date = timezone.now().date() + timedelta(days=90)
        super().save(*args, **kwargs)
