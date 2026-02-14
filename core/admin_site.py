from django.contrib.admin import AdminSite
from django.db.models import Sum, Count
from django.utils.translation import gettext_lazy as _
# Import models inside methods or check app readiness if at module level, 
# but site is usually loaded at URL conf time.
# To be safe, import inside index.

class HandramoutAdminSite(AdminSite):
    site_header = _("Hadramout Village Administration")
    site_title = _("Hadramout Admin")
    index_title = _("Dashboard")

    def index(self, request, extra_context=None):
        from accounts.models import Doctor, Vendor
        from events.models import Event, Voucher
        from core.models import Transaction

        # Gather statistics
        stats = {
            'total_doctors': Doctor.objects.count(),
            'total_vendors': Vendor.objects.count(),
            'active_events': Event.objects.count(), # Maybe filter by date
            'total_vouchers': Voucher.objects.count(),
            'total_spent': Transaction.objects.aggregate(Sum('amount_spent'))['amount_spent__sum'] or 0,
            'total_transactions': Transaction.objects.count(),
        }

        extra_context = extra_context or {}
        extra_context.update(stats)
        return super().index(request, extra_context)

admin_site = HandramoutAdminSite(name='handramout_admin')
