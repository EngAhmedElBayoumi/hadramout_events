from django.http import JsonResponse
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from accounts.models import Doctor, Vendor
from events.models import Event, Voucher
from .models import Transaction, PharmaceuticalCompany

@staff_member_required
def dashboard_stats_api(request):
    # Time ranges
    now = timezone.now()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)

    # 1. KPI Cards
    total_revenue = Transaction.objects.aggregate(total=Sum('amount_spent'))['total'] or 0
    revenue_7d = Transaction.objects.filter(transaction_date__gte=last_7_days).aggregate(total=Sum('amount_spent'))['total'] or 0
    
    total_orders = Transaction.objects.count()
    orders_7d = Transaction.objects.filter(transaction_date__gte=last_7_days).count()

    total_doctors = Doctor.objects.count()
    total_vendors = Vendor.objects.count()
    active_vouchers = Voucher.objects.filter(is_active=True).count()

    # Growth Calculation (Simple prev period comparison)
    prev_7d_start = last_7_days - timedelta(days=7)
    revenue_prev_7d = Transaction.objects.filter(transaction_date__gte=prev_7d_start, transaction_date__lt=last_7_days).aggregate(total=Sum('amount_spent'))['total'] or 0
    
    revenue_growth = 0
    if revenue_prev_7d > 0:
        revenue_growth = ((revenue_7d - revenue_prev_7d) / revenue_prev_7d) * 100
    elif revenue_7d > 0:
        revenue_growth = 100

    # 2. Revenue Chart (Last 30 days)
    chart_labels = []
    chart_data = []
    current = last_30_days
    while current <= now:
        next_day = current + timedelta(days=1)
        day_total = Transaction.objects.filter(transaction_date__gte=current, transaction_date__lt=next_day).aggregate(total=Sum('amount_spent'))['total'] or 0
        chart_labels.append(current.strftime('%d %b'))
        chart_data.append(round(float(day_total), 2))
        current = next_day

    # 3. Top Vendors (by Revenue)
    top_vendors_qs = Vendor.objects.annotate(total_revenue=Sum('transaction__amount_spent')).order_by('-total_revenue')[:5]
    top_vendors = [{'name': v.name, 'revenue': round(float(v.total_revenue or 0), 2)} for v in top_vendors_qs]


    data = {
        'kpi': {
            'total_revenue': round(float(total_revenue), 2),
            'revenue_7d': round(float(revenue_7d), 2),
            'revenue_growth': round(float(revenue_growth), 2),
            'total_orders': total_orders,
            'orders_7d': orders_7d,
            'total_doctors': total_doctors,
            'total_vendors': total_vendors,
            'active_vouchers': active_vouchers,
        },
        'chart': {
            'labels': chart_labels,
            'data': chart_data,
        },
        'top_vendors': top_vendors,
    }

    return JsonResponse(data)
