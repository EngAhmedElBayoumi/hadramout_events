from django.contrib import admin
from .models import Event, Voucher

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'company', 'voucher_value')
    list_filter = ('date', 'company')
    search_fields = ('name', 'company__name')
    filter_horizontal = ('doctors',) # Better UI for M2M

@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'event', 'initial_value', 'current_balance', 'expiry_date', 'is_active')
    list_filter = ('is_active', 'expiry_date', 'event')
    search_fields = ('doctor__name', 'event__name')
    readonly_fields = ('issue_date',)
