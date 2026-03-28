from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import Sum
from django.http import HttpResponse
from django.core.mail import send_mail
from .models import User, Doctor, Vendor, Specialty, Delegate
from .utils import generate_doctor_card_pdf
from .forms import UserCreationForm
from events.models import Voucher, Event, VoucherTransfer
from core.models import Transaction
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import action
from django.utils.translation import gettext_lazy as _
from django.template.response import TemplateResponse
from django.conf import settings
from unfold.widgets import UnfoldAdminPasswordInput
# import user




@admin.register(Specialty)
class SpecialtyAdmin(ModelAdmin):
    search_fields = ('name',)

@admin.register(Delegate)
class DelegateAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'get_companies_count', 'get_specialties_count')
    search_fields = ('name', 'phone')
    filter_horizontal = ('companies', 'specialties')

    def get_companies_count(self, obj):
        count = obj.companies.count()
        return _("{} Companies").format(count) if count > 0 else _("General (All Companies)")
    get_companies_count.short_description = _("Companies")

    def get_specialties_count(self, obj):
        count = obj.specialties.count()
        return _("{} Specialties").format(count) if count > 0 else _("General (All Specialties)")
    get_specialties_count.short_description = _("Specialties")

class DoctorProfileInline(StackedInline):
    model = Doctor
    extra = 1
    max_num = 1
    can_delete = False
    verbose_name = _("Doctor Profile")
    verbose_name_plural = _("Doctor Profiles")
    tab = True
    model = Doctor
    extra = 1
    max_num = 1
    can_delete = False
    verbose_name = _("Doctor Profile")
    verbose_name_plural = _("Doctor Profiles")
    tab = True

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
    
    inlines = [DoctorProfileInline]

    def get_inline_instances(self, request, obj=None):
        inline_instances = []
        for inline_class in self.inlines:
            inline = inline_class(self.model, self.admin_site)
            if obj:
                if isinstance(inline, DoctorProfileInline) and obj.type == 'DOCTOR':
                    inline_instances.append(inline)
            else:
                inline_instances.append(inline)
        return inline_instances
    
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

class VoucherTransferInline(TabularInline):
    model = VoucherTransfer
    fk_name = 'from_doctor'
    extra = 0
    can_delete = False
    readonly_fields = ('to_doctor', 'voucher', 'transfer_date')
    fields = ('to_doctor', 'voucher', 'transfer_date')
    verbose_name = "تحويل صادر"
    verbose_name_plural = "سجل التحويلات الصادرة"
    tab = True

@admin.register(Doctor)
class DoctorAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'specialty', 'get_current_balance')
    list_filter = ('specialty',)
    search_fields = ('name', 'phone', 'email')
    autocomplete_fields = ('user', 'specialty')
    actions = ['export_doctor_cards_pdf']
    
    readonly_fields = ('get_current_balance', 'card_preview_tab')
    
    inlines = [VoucherInline, TransactionInline, EventInline, VoucherTransferInline]
    
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
                (_("Transfers History"), ("VoucherTransferInline",)),
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

from django import forms
from django.contrib.auth import get_user_model

User = getattr(settings, 'AUTH_USER_MODEL', 'accounts.User')
UserObject = get_user_model()

class VendorAdminForm(forms.ModelForm):
    vendor_password = forms.CharField(label=_('Password (for new User)'), widget=UnfoldAdminPasswordInput, required=False)

    class Meta:
        model = Vendor
        fields = ('name', 'contact_person', 'phone', 'email', 'address', 'category', 'role', 'has_management_fee', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and getattr(self.instance, 'user', None):
            self.fields['vendor_password'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:
            name = cleaned_data.get('name')
            v_pass = cleaned_data.get('vendor_password')
            if not name or not v_pass:
                raise forms.ValidationError(_("Name and Password are required to create the account."))
            
            # Derived username
            generated_username = name.strip().replace(' ', '_')
            if UserObject.objects.filter(username=generated_username).exists():
                raise forms.ValidationError(_("A user with a name that generates the username '{}' already exists. Please use a slightly different name.").format(generated_username))
        return cleaned_data

class CashierInlineForm(forms.ModelForm):
    cashier_password = forms.CharField(label=_("Cashier Password"), widget=UnfoldAdminPasswordInput, required=False)

    class Meta:
        model = Vendor
        fields = ('name', 'contact_person', 'phone', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and getattr(self.instance, 'user', None):
            self.fields['cashier_password'].disabled = True
            self.fields['contact_person'].required = False
            self.fields['phone'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:
            name = cleaned_data.get('name')
            c_pass = cleaned_data.get('cashier_password')
            if not name or not c_pass:
                raise forms.ValidationError(_("Name and Password required for new cashier."))
            
            generated_username = name.strip().replace(' ', '_')
            if UserObject.objects.filter(username=generated_username).exists():
                raise forms.ValidationError(_("Username '{}' already exists.").format(generated_username))
        return cleaned_data

class CashierInline(StackedInline):
    model = Vendor
    fk_name = 'parent_vendor'
    form = CashierInlineForm
    extra = 1
    verbose_name = _('Cashier')
    verbose_name_plural = _('Cashiers')
    fields = ('name', 'contact_person', 'phone', 'cashier_password', 'is_active')

@admin.register(Vendor)
class VendorAdmin(ModelAdmin):
    form = VendorAdminForm
    list_display = ('name', 'contact_person', 'phone', 'category', 'is_active', 'has_management_fee')
    list_filter = ('category', 'is_active', 'has_management_fee')
    search_fields = ('name', 'contact_person')
    autocomplete_fields = ('parent_vendor',)
    inlines = [CashierInline]

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'vendor_password', 'contact_person', 'phone', 'email', 'address', 'category'),
            'description': _('The Name field will also be used as the login username (spaces will be replaced by underscores).')
        }),
        (_('Access Control'), {
            'fields': ('is_active', 'has_management_fee'),
            'description': _('Control account activation and management fee settings.')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='ADMIN')

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new Vendor
            if not obj.user_id:
                generated_username = obj.name.strip().replace(' ', '_')
                user = UserObject.objects.create_user(
                    username=generated_username,
                    password=form.cleaned_data['vendor_password'],
                    email=obj.email,
                    phone=obj.phone,
                    type='VENDOR',
                    is_active=obj.is_active
                )
                obj.user = user
            obj.role = 'ADMIN'
        else:  # Updating existing Vendor
            if obj.user:
                obj.user.is_active = obj.is_active
                obj.user.save()
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        if formset.model == Vendor:
            instances = formset.save(commit=False)
            for instance in instances:
                if not getattr(instance, 'user_id', None):
                    for f in formset.forms:
                        if f.instance == instance:
                            c_pass = f.cleaned_data.get('cashier_password')
                            generated_username = instance.name.strip().replace(' ', '_')
                            user = UserObject.objects.create_user(
                                username=generated_username,
                                password=c_pass,
                                type='VENDOR',
                                first_name=instance.name,
                                is_active=instance.is_active
                            )
                            instance.user = user
                            instance.role = 'CASHIER'
                            if not instance.email:
                                instance.email = f"{generated_username}@hadramoutevents.com"
                            if not getattr(instance, 'category', None):
                                instance.category = getattr(instance.parent_vendor, 'category', 'Cashier')
                            break
                else:
                    # Update cashier user active status
                    if instance.user:
                        instance.user.is_active = instance.is_active
                        instance.user.save()
                instance.save()
            formset.save_m2m()
            for obj in formset.deleted_objects:
                obj.delete()
        else:
            super().save_formset(request, form, formset, change)
