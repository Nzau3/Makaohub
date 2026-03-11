from django.contrib import admin
from .models import MpesaTransaction, MpesaAccessToken


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'transaction_type', 'amount', 'phone_number', 'user', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['transaction_id', 'merchant_request_id', 'checkout_request_id', 'phone_number', 'reference']
    readonly_fields = ['transaction_id', 'merchant_request_id', 'checkout_request_id', 'created_at', 'updated_at', 'raw_response']


@admin.register(MpesaAccessToken)
class MpesaAccessTokenAdmin(admin.ModelAdmin):
    list_display = ['access_token', 'expires_at', 'created_at']
    readonly_fields = ['access_token', 'expires_at', 'created_at']
