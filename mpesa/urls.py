from django.urls import path
from . import views

app_name = 'mpesa'

urlpatterns = [
    # STK Push endpoints
    path('stk-push/', views.initiate_stk_push, name='stk_push'),
    path('query-status/', views.query_payment_status, name='query_status'),

    # Callback endpoint (must be publicly accessible for M-Pesa)
    path('callback/', views.mpesa_callback, name='callback'),
]