from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import Sum
from django.http import HttpResponse
from django.core.mail import send_mail
from .models import User, Doctor, Vendor, Specialty, Delegate
from .utils import generate_doctor_card_pdf
from .forms import UserCreationForm
from events.models import Voucher, Event
from core.models import Transaction
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from django.utils.translation import gettext_lazy as _
from django.template.response import TemplateResponse
from django.conf import settings
# import user




@admin.register(Specialty)
class SpecialtyAdmin(ModelAdmin):
    search_fields = ('name',)

@admin.register(Delegate)
class DelegateAdmin(ModelAdmin):
    search_fields = ('name', 'phone')

from django.urls import reverse
from django.utils.html import format_html

@admin.register(User)
class CustomUserAdmin(UserAdmin, ModelAdmin):
    add_form = UserCreationForm
    checks_class = UserAdmin.checks_class
    list_display = ('username', 'email', 'phone', 'first_name', 'last_name', 'change_password_link')
    
    # Override fieldsets and add_fieldsets to avoid including 'usable_password'
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'type')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'phone', 'type'),
        }),
    )
    
    # Alternatively, use exclude to remove usable_password if it appears
    # exclude = ('usable_password',)
    
    def change_password_link(self, obj):
        url = reverse('admin:auth_user_password_change', args=[obj.pk])
        return format_html('<a class="button" href="{}">تغيير كلمة المرور</a>', url)
    change_password_link.short_description = 'تغيير كلمة المرور'

    def save_model(self, request, obj, form, change):
        if not change:  # New user being created

            if form.cleaned_data.get('type') == 'ADMIN' or form.cleaned_data.get('type') == 'admin':  
                obj.is_superuser = True


            password = form.cleaned_data.get('password1')
            if password:
                username = obj.username
                email = obj.email
                phone = obj.phone
                site_url = request.build_absolute_uri('/')
                
                subject = _('Account Created - Hadramout Events')
                message = _(
                    'Welcome! Your account has been created.\n\n'
                    'Site: {site_url}\n'
                    'Username: {username}\n'
                    'Email: {email}\n'
                    'Phone: {phone}\n'
                    'Password: {password}\n'
                ).format(site_url=site_url, username=username, email=email, phone=phone, password=password)
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,  # Uses DEFAULT_FROM_EMAIL
                        [email],
                        fail_silently=False,
                    )
                    messages.success(request, _('Welcome email sent to {email}').format(email=email))
                except Exception as e:
                    messages.error(request, _('Failed to send welcome email: {error}').format(error=str(e)))
        
        super().save_model(request, obj, form, change)


class VoucherInline(TabularInline):
    model = Voucher
    extra = 0
    readonly_fields = ('issue_date',)
    fields = ('event', 'initial_value', 'current_balance', 'issue_date', 'expiry_date', 'is_active')
    tab = True

class TransactionInline(TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ('transaction_date', 'invoice_number', 'created_by')
    fields = ('invoice_number', 'vendor', 'created_by', 'amount_spent', 'total_deducted', 'transaction_date')
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
    list_filter = ('specialty',)
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

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        
        # Support filtering by specialties passed via query parameter (for dynamic filtering in Event admin)
        specialties_ids = request.GET.get('specialties_ids')
        if specialties_ids:
            try:
                ids = [int(x) for x in specialties_ids.split(',') if x.isdigit()]
                if ids:
                    queryset = queryset.filter(specialty_id__in=ids)
            except (ValueError, TypeError):
                pass
                
        return queryset, use_distinct

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
        buffer = generate_doctor_card_pdf(queryset, request=request)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="doctor_cards.pdf"'
        return response

@admin.register(Vendor)
class VendorAdmin(ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'category', 'role', 'has_management_fee')
    list_filter = ('category', 'role')
    search_fields = ('name', 'contact_person')
    autocomplete_fields = ('user',)
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('user', 'name', 'contact_person', 'phone', 'email', 'address', 'category')
        }),
        (_('Access Control'), {
            'fields': ('role', 'has_management_fee'),
            'description': _('Vendor Admin has full access to dashboard and search. Vendor Cashier can only process transactions via QR code scan.')
        }),
    )
