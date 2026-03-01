from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
from .models import Event, Voucher
from unfold.admin import ModelAdmin

class NextWeekFilter(admin.SimpleListFilter):
    title = 'الأسبوع المقبل'
    parameter_name = 'next_week'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'نعم'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            now = timezone.now().date()
            start_of_next_week = now + timedelta(days=(7 - now.weekday()))
            end_of_next_week = start_of_next_week + timedelta(days=6)
            return queryset.filter(date__range=[start_of_next_week, end_of_next_week])
        return queryset

@admin.register(Event)
class EventAdmin(ModelAdmin):
    list_display = ('name', 'date', 'company', 'voucher_value', 'payment_type')
    list_filter = ('date', 'company', 'payment_type', NextWeekFilter)
    search_fields = ('name', 'company__name')
    autocomplete_fields = ('company', 'doctors', 'delegates', 'specialties')
    filter_horizontal = ('doctors', 'delegates', 'specialties')
    change_list_template = 'admin/events/event/change_list.html'
    fields = ('name', 'date', 'company', 'payment_type', 'voucher_value', 'voucher_expiry_days', 'delegates', 'specialties', 'doctors', 'notes')

    class Media:
        js = ('admin/js/event_filter.js',)

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            # We need to pass the queryset results to the template for the calendar
            if hasattr(response, 'context_data'):
                # Extract results from the Unfold/Django changelist
                cl = response.context_data['cl']
                response.context_data['results'] = cl.result_list
        except (AttributeError, KeyError):
            pass
        return response

@admin.register(Voucher)
class VoucherAdmin(ModelAdmin):
    list_display = ('doctor', 'event', 'company', 'initial_value', 'current_balance', 'expiry_date', 'is_active')
    list_filter = ('is_active', 'expiry_date', 'event', 'company')
    search_fields = ('doctor__name', 'event__name', 'company__name')
    autocomplete_fields = ('doctor', 'event', 'company')
    readonly_fields = ('issue_date',)
