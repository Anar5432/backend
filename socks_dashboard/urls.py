from django.urls import path
from dashboard import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # HTMX partial endpoints — return HTML fragments
    path('htmx/kpis/', views.htmx_kpis, name='htmx_kpis'),
    path('htmx/pipeline/', views.htmx_pipeline, name='htmx_pipeline'),
    path('htmx/orders/', views.htmx_orders, name='htmx_orders'),
    path('htmx/order/<int:order_id>/', views.htmx_order_detail, name='htmx_order_detail'),
    path('htmx/chart/', views.htmx_chart, name='htmx_chart'),

    # JSON API for JavaScript charts
    path('api/chart-data/', views.api_chart_data, name='api_chart_data'),
    path('api/stock-data/', views.api_stock_data, name='api_stock_data'),
    path('api/estimate/', views.api_estimate, name='api_estimate'),
]
