from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class Types(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        DOCTOR = 'DOCTOR', _('Doctor')
        VENDOR = 'VENDOR', _('Vendor')

    type = models.CharField(
        _('Type'), max_length=50, choices=Types.choices, default=Types.ADMIN
    )
    phone = models.CharField(_('Phone Number'), max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username

class Specialty(models.Model):
    name = models.CharField(_('Name'), max_length=100, unique=True)

    class Meta:
        verbose_name = _('Specialty')
        verbose_name_plural = _('Specialties')

    def __str__(self):
        return self.name

class Delegate(models.Model):
    name = models.CharField(_('Name'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20, unique=True)

    class Meta:
        verbose_name = _('Delegate')
        verbose_name_plural = _('Delegates')

    def __str__(self):
        return self.name

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile', verbose_name=_('User'))
    name = models.CharField(_('Name'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20, unique=True)
    email = models.EmailField(_('Email'), unique=True)
    specialty = models.ForeignKey(Specialty, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Specialty'))
    qr_code = models.CharField(_('QR Code'), max_length=255, blank=True, null=True) # URL or path
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Doctor')
        verbose_name_plural = _('Doctors')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.qr_code:
            import uuid
            self.qr_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)
    
    def get_qr_code_url(self):
        """Generate the full URL for QR code scanning"""
        return f"/scan/{self.qr_code}/"

class Vendor(models.Model):
    class VendorRoles(models.TextChoices):
        ADMIN = 'ADMIN', _('Vendor Admin')
        CASHIER = 'CASHIER', _('Vendor Cashier')

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile', verbose_name=_('User'))
    name = models.CharField(_('Name'), max_length=255, unique=True)
    contact_person = models.CharField(_('Contact Person'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20)
    email = models.EmailField(_('Email'))
    address = models.TextField(_('Address'))
    category = models.CharField(_('Category'), max_length=100) # e.g. Supermarket, Restaurant
    role = models.CharField(
        _('Role'), max_length=20, choices=VendorRoles.choices, default=VendorRoles.ADMIN,
        help_text=_('Vendor Admin has full access, Cashier can only process transactions via QR scan')
    )
    has_management_fee = models.BooleanField(_('Has Management Fee'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Vendor')
        verbose_name_plural = _('Vendors')

    def __str__(self):
        return self.name
