from django.contrib import admin
from .models import PharmaceuticalCompany, Transaction, VendorSettlement
from unfold.admin import ModelAdmin

@admin.register(PharmaceuticalCompany)
class PharmaceuticalCompanyAdmin(ModelAdmin):
    list_display = ('name', 'contact_person', 'phone')
    search_fields = ('name',)

@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ('invoice_number', 'doctor', 'vendor', 'amount_spent', 'total_deducted', 'transaction_date')
    list_filter = ('transaction_date', 'vendor')
    search_fields = ('invoice_number', 'doctor__name', 'vendor__name')
    autocomplete_fields = ('doctor', 'vendor', 'voucher')
    readonly_fields = ('transaction_date', 'invoice_number')

@admin.register(VendorSettlement)
class VendorSettlementAdmin(ModelAdmin):
    list_display = ('vendor', 'amount_settled', 'settlement_date')
    list_filter = ('settlement_date', 'vendor')
    search_fields = ('vendor__name',)
    autocomplete_fields = ('vendor',)
