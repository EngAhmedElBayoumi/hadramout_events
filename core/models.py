from django.db import models
from django.utils.translation import gettext_lazy as _

class PharmaceuticalCompany(models.Model):
    name = models.CharField(_('Name'), max_length=255, unique=True)
    contact_person = models.CharField(_('Contact Person'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20)
    email = models.EmailField(_('Email'))
    address = models.TextField(_('Address'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Pharmaceutical Company')
        verbose_name_plural = _('Pharmaceutical Companies')

    def __str__(self):
        return self.name

class VendorSettlement(models.Model):
    vendor = models.ForeignKey('accounts.Vendor', on_delete=models.CASCADE, verbose_name=_('Vendor'))
    amount_settled = models.DecimalField(_('Amount Settled'), max_digits=12, decimal_places=2)
    settlement_date = models.DateField(_('Settlement Date'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Vendor Settlement')
        verbose_name_plural = _('Vendor Settlements')

    def __str__(self):
        return f"{self.vendor} - {self.amount_settled} - {self.settlement_date}"

class Transaction(models.Model):
    voucher = models.ForeignKey('events.Voucher', on_delete=models.PROTECT, verbose_name=_('Voucher'))  # Protect to keep history
    vendor = models.ForeignKey('accounts.Vendor', on_delete=models.PROTECT, verbose_name=_('Vendor'))
    doctor = models.ForeignKey('accounts.Doctor', on_delete=models.PROTECT, verbose_name=_('Doctor'))
    amount_spent = models.DecimalField(_('Amount Spent'), max_digits=10, decimal_places=2)
    management_fee_percentage = models.DecimalField(_('Management Fee Percentage'), max_digits=5, decimal_places=2, default=25.00)
    management_fee_amount = models.DecimalField(_('Management Fee Amount'), max_digits=10, decimal_places=2)
    total_deducted = models.DecimalField(_('Total Deducted'), max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(_('Transaction Date'), auto_now_add=True)
    items_description = models.TextField(_('Items Description'), blank=True)
    invoice_number = models.CharField(_('Invoice Number'), max_length=100, unique=True)
    
    # Link to settlement
    settlement = models.ForeignKey(
        VendorSettlement, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions',
        verbose_name=_('Settlement')
    )

    class Meta:
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')

    def __str__(self):
        return f"{self.invoice_number} - {self.doctor} at {self.vendor}"
