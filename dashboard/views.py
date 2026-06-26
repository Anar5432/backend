import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from . import queries


def dashboard(request):
    """Main dashboard page — full page load with initial data."""
    sector = request.GET.get('sector', 'corab')
    if sector not in ['corab', 'isci', 'underwear']:
        sector = 'corab'

    data = queries.get_orders(sector)
    companies = data['companies']
    stages = data['stages']
    standard_productions = data.get('standard_productions', [])
    shifts = queries.get_todays_shifts(sector)
    forecast = queries.get_capacity_forecast(sector)
    rules = queries.get_sector_rules(sector)

    context = {
        'sector': sector,
        'rules': rules,
        'companies': companies,
        'standard_productions': standard_productions,
        'stages': stages,
        'shifts': shifts,
        'forecast': forecast,
        'refresh_seconds': getattr(settings, 'DASHBOARD_REFRESH_SECONDS', 300),
    }
    return render(request, 'dashboard/index.html', context)


# ── HTMX PARTIALS ──────────────────────────────────────────────────────────

@require_GET
def htmx_kpis(request):
    """Refresh just the KPI cards strip."""
    sector = request.GET.get('sector', 'corab')
    kpis = queries.get_kpis(sector)
    return render(request, 'dashboard/partials/kpis.html', {'kpis': kpis})


@require_GET
def htmx_pipeline(request):
    """Refresh the production pipeline bar."""
    sector = request.GET.get('sector', 'corab')
    pipeline = queries.get_pipeline(sector)
    shifts = queries.get_todays_shifts(sector)
    return render(request, 'dashboard/partials/pipeline.html', {
        'pipeline': pipeline,
        'shifts': shifts,
    })


@require_GET
def htmx_orders(request):
    """HTMX endpoint to refresh just the orders list."""
    sector = request.GET.get('sector', 'corab')
    data = queries.get_orders(sector)
    return render(request, 'dashboard/partials/orders.html', {
        'companies': data['companies'],
        'standard_productions': data.get('standard_productions', []),
        'sector': sector,
    })


@require_GET
def htmx_order_detail(request, order_id):
    """Slide-in detail panel for one order."""
    detail = queries.get_order_detail(order_id)
    return render(request, 'dashboard/partials/order_detail.html', {'detail': detail})


@require_GET
def htmx_chart(request):
    """Refresh the bottom charts section."""
    top_products = queries.get_top_products(10)
    stock = queries.get_stock_by_warehouse()
    return render(request, 'dashboard/partials/charts.html', {
        'top_products': top_products,
        'stock': stock,
    })


# ── JSON API (for Chart.js) ─────────────────────────────────────────────────

@require_GET
def api_chart_data(request):
    data = queries.get_monthly_chart_data()
    # Convert Decimal to float for JSON serialisation
    for item in data.get('sales', []):
        item['revenue'] = float(item.get('revenue') or 0)
        item['qty_sold'] = float(item.get('qty_sold') or 0)
    for item in data.get('production', []):
        item['qty_produced'] = float(item.get('qty_produced') or 0)
    return JsonResponse(data)


@require_GET
def api_stock_data(request):
    stock = queries.get_stock_by_warehouse()
    for item in stock:
        item['total_qty'] = float(item.get('total_qty') or 0)
    return JsonResponse({'stock': stock})

@require_GET
def api_estimate(request):
    cat = request.GET.get('cat', '')
    qty = request.GET.get('qty', 0)
    workers = request.GET.get('workers', 10)
    
    from .queue_engine import get_whatif_estimate
    
    try:
        data = get_whatif_estimate(cat, float(qty), float(workers))
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
