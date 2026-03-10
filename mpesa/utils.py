"""
M-Pesa Daraja API utilities for Kenya
"""

import base64
import json
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import MpesaAccessToken


class MpesaAPI:
    """M-Pesa Daraja API client."""

    def __init__(self):
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.shortcode = getattr(settings, 'MPESA_SHORTCODE', '')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        self.base_url = getattr(settings, 'MPESA_BASE_URL', 'https://sandbox.safaricom.co.ke')

        if not all([self.consumer_key, self.consumer_secret, self.shortcode]):
            raise ValueError("M-Pesa credentials not configured in settings")

    def get_access_token(self):
        """Get or retrieve cached access token."""
        # Try to get cached token
        token_obj = MpesaAccessToken.objects.filter(expires_at__gt=timezone.now()).first()

        if token_obj:
            return token_obj.access_token

        # Generate new token
        auth = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()

        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/json'
        }

        response = requests.get(f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials", headers=headers)

        if response.status_code == 200:
            data = response.json()
            expires_at = timezone.now() + timedelta(seconds=data.get('expires_in', 3600))

            # Save token
            token_obj = MpesaAccessToken.objects.create(
                access_token=data['access_token'],
                expires_at=expires_at
            )

            return data['access_token']
        else:
            raise Exception(f"Failed to get access token: {response.text}")

    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK push payment request."""

        access_token = self.get_access_token()

        # Format phone number (remove + and ensure 254 format)
        phone_number = phone_number.lstrip('+')
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]

        # Generate timestamp and password
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": getattr(settings, 'MPESA_CALLBACK_URL', ''),
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers
        )

        return response.json()

    def query_stk_status(self, checkout_request_id):
        """Query STK push payment status."""

        access_token = self.get_access_token()

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f"{self.shortcode}{self.passkey}{timestamp}".encode()
        ).decode()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            f"{self.base_url}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers=headers
        )

        return response.json()


def format_phone_number(phone_number):
    """Format phone number to M-Pesa format (254XXXXXXXXX)."""
    if not phone_number:
        return phone_number

    # Remove all non-digit characters
    phone_number = ''.join(filter(str.isdigit, phone_number))

    # Handle different formats
    if phone_number.startswith('254'):
        return phone_number
    elif phone_number.startswith('0'):
        return '254' + phone_number[1:]
    elif phone_number.startswith('7') or phone_number.startswith('1'):
        return '254' + phone_number
    else:
        return phone_number