from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Doctor, Vendor
from unfold.admin import ModelAdmin

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'type', 'is_staff')
    list_filter = ('type', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('type',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('type',)}),
    )

@admin.register(Doctor)
class DoctorAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'specialty')
    search_fields = ('name', 'phone', 'email')

@admin.register(Vendor)
class VendorAdmin(ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'contact_person')
