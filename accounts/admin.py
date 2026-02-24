from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Sum
from django.http import HttpResponse
from .models import User, Doctor, Vendor, Specialty, Delegate
from .utils import generate_doctor_card_pdf
from events.models import Voucher, Event
from core.models import Transaction
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from django.utils.translation import gettext_lazy as _
from django.template.response import TemplateResponse

@admin.register(Specialty)
class SpecialtyAdmin(ModelAdmin):
    search_fields = ('name',)

@admin.register(Delegate)
class DelegateAdmin(ModelAdmin):
    search_fields = ('name', 'phone')


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

class VoucherInline(TabularInline):
    model = Voucher
    extra = 0
    readonly_fields = ('issue_date',)
    fields = ('event', 'initial_value', 'current_balance', 'issue_date', 'expiry_date', 'is_active')
    tab = True

class TransactionInline(TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ('transaction_date', 'invoice_number')
    fields = ('invoice_number', 'vendor', 'amount_spent', 'total_deducted', 'transaction_date')
    tab = True

class EventInline(TabularInline):
    model = Event.doctors.through
    verbose_name = _("Session")
    verbose_name_plural = _("Sessions")
    extra = 0
    tab = True

@admin.register(Doctor)
class DoctorAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'specialty')
    search_fields = ('name', 'phone', 'email')
    autocomplete_fields = ('user', 'specialty')
    actions = ['export_doctor_cards_pdf']
    
    readonly_fields = ('get_current_balance', 'card_preview_tab')
    
    inlines = [VoucherInline, TransactionInline, EventInline]
    
    tab_groups = (
        (
            _("Basic Information"),
            [
                (_("Personal Data"), ("user", "name", "phone", "email")),
                (_("Professional Data"), ("specialty", "qr_code")),
            ],
        ),
        (
            _("Financials"),
            [
                (_("Balance Summary"), ("get_current_balance",)),
                (_("Vouchers History"), ("VoucherInline",)),
                (_("Purchases History"), ("TransactionInline",)),
            ],
        ),
        (
            _("Attendance"),
            [
                (_("Sessions History"), ("EventInline",)),
            ],
        ),
        (
            _("Business Card"),
            [
                (_("Preview"), ("card_preview_tab",)),
            ],
        ),
    )

    def get_current_balance(self, obj):
        if obj.pk:
            balance = obj.vouchers.filter(is_active=True).aggregate(total=Sum('current_balance'))['total'] or 0
            return f"{balance} ج.م"
        return "0 ج.م"
    get_current_balance.short_description = _("Current Balance")

    def card_preview_tab(self, obj):
        if not obj.pk:
            return _("Save the doctor first to see the card.")
        from django.utils.safestring import mark_safe
        from django.template.loader import render_to_string
        html = render_to_string("admin/accounts/doctor/card_preview.html", {"original": obj})
        return mark_safe(html)
    card_preview_tab.short_description = _("Card Preview")

    @action(description=_("Export Doctor Cards (PDF)"))
    def export_doctor_cards_pdf(self, request, queryset):
        buffer = generate_doctor_card_pdf(queryset)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="doctor_cards.pdf"'
        return response

@admin.register(Vendor)
class VendorAdmin(ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'contact_person')
    autocomplete_fields = ('user',)
