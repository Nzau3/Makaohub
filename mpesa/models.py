from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class MpesaTransaction(models.Model):
    """Model to store M-Pesa transaction details."""

    class TransactionType(models.TextChoices):
        STK_PUSH = 'stk_push', 'STK Push'
        C2B = 'c2b', 'Customer to Business'
        B2C = 'b2c', 'Business to Customer'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    # Unique transaction identifiers
    transaction_id = models.CharField(max_length=50, unique=True, help_text="M-Pesa transaction ID")
    merchant_request_id = models.CharField(max_length=50, blank=True, null=True)
    checkout_request_id = models.CharField(max_length=50, blank=True, null=True)

    # Transaction details
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.STK_PUSH
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15, help_text="Phone number in format 254XXXXXXXXX")

    # Associated user and reference
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mpesa_transactions')
    reference = models.CharField(max_length=100, help_text="Internal reference (e.g., property_id, invoice_id)")

    # Status and timestamps
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Response data
    response_code = models.CharField(max_length=10, blank=True, null=True)
    response_description = models.TextField(blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['checkout_request_id']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.transaction_id} - {self.amount}"


class MpesaAccessToken(models.Model):
    """Model to cache M-Pesa access tokens."""

    access_token = models.TextField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Access Token expiring at {self.expires_at}"
