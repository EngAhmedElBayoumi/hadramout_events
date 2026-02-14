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

    def __str__(self):
        return self.username

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile', verbose_name=_('User'))
    name = models.CharField(_('Name'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20, unique=True)
    email = models.EmailField(_('Email'), unique=True)
    specialty = models.CharField(_('Specialty'), max_length=100)
    qr_code = models.CharField(_('QR Code'), max_length=255, blank=True, null=True) # URL or path
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Doctor')
        verbose_name_plural = _('Doctors')

    def __str__(self):
        return self.name

class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile', verbose_name=_('User'))
    name = models.CharField(_('Name'), max_length=255, unique=True)
    contact_person = models.CharField(_('Contact Person'), max_length=255)
    phone = models.CharField(_('Phone'), max_length=20)
    email = models.EmailField(_('Email'))
    address = models.TextField(_('Address'))
    category = models.CharField(_('Category'), max_length=100) # e.g. Supermarket, Restaurant
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Vendor')
        verbose_name_plural = _('Vendors')

    def __str__(self):
        return self.name
