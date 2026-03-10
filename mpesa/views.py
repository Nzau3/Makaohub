import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import MpesaTransaction
from .utils import MpesaAPI, format_phone_number


@login_required
@require_POST
def initiate_stk_push(request):
    """Initiate STK push payment for logged-in user."""

    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        phone_number = data.get('phone_number')
        reference = data.get('reference', f"user_{request.user.id}")

        if not amount or not phone_number:
            return JsonResponse({'error': 'Amount and phone number are required'}, status=400)

        # Format phone number
        phone_number = format_phone_number(phone_number)

        # Initialize M-Pesa API
        mpesa_api = MpesaAPI()

        # Initiate STK push
        response = mpesa_api.stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=reference,
            transaction_desc=f"Payment for {reference}"
        )

        if response.get('ResponseCode') == '0':
            # Create transaction record
            transaction = MpesaTransaction.objects.create(
                transaction_id=response.get('CheckoutRequestID', ''),
                merchant_request_id=response.get('MerchantRequestID', ''),
                checkout_request_id=response.get('CheckoutRequestID', ''),
                transaction_type='stk_push',
                amount=amount,
                phone_number=phone_number,
                user=request.user,
                reference=reference,
                status='pending',
                raw_response=response
            )

            return JsonResponse({
                'success': True,
                'checkout_request_id': response.get('CheckoutRequestID'),
                'merchant_request_id': response.get('MerchantRequestID'),
                'message': 'STK push initiated successfully'
            })
        else:
            return JsonResponse({
                'error': response.get('ResponseDescription', 'STK push failed')
            }, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def query_payment_status(request):
    """Query payment status for a transaction."""

    checkout_request_id = request.GET.get('checkout_request_id')

    if not checkout_request_id:
        return JsonResponse({'error': 'Checkout request ID is required'}, status=400)

    try:
        mpesa_api = MpesaAPI()
        response = mpesa_api.query_stk_status(checkout_request_id)

        # Update transaction status if found
        transaction = MpesaTransaction.objects.filter(
            checkout_request_id=checkout_request_id,
            user=request.user
        ).first()

        if transaction:
            if response.get('ResponseCode') == '0':
                result_code = response.get('ResultCode')
                if result_code == '0':
                    transaction.status = 'completed'
                elif result_code in ['1', '1032', '1037', '2001']:
                    transaction.status = 'cancelled'
                else:
                    transaction.status = 'failed'

                transaction.response_code = str(result_code)
                transaction.response_description = response.get('ResultDesc', '')
                transaction.raw_response = response
                transaction.save()

        return JsonResponse(response)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """Handle M-Pesa callback for payment confirmation."""

    try:
        callback_data = json.loads(request.body)

        # Extract transaction details
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})

        if stk_callback:
            merchant_request_id = stk_callback.get('MerchantRequestID')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')

            # Find and update transaction
            transaction = MpesaTransaction.objects.filter(
                checkout_request_id=checkout_request_id
            ).first()

            if transaction:
                if result_code == 0:
                    # Payment successful
                    callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])

                    # Extract transaction details
                    for item in callback_metadata:
                        if item.get('Name') == 'MpesaReceiptNumber':
                            transaction.transaction_id = item.get('Value')
                        elif item.get('Name') == 'TransactionDate':
                            # Could parse date if needed
                            pass
                        elif item.get('Name') == 'PhoneNumber':
                            transaction.phone_number = str(item.get('Value'))
                        elif item.get('Name') == 'Amount':
                            transaction.amount = item.get('Value')

                    transaction.status = 'completed'
                else:
                    transaction.status = 'failed'

                transaction.response_code = str(result_code)
                transaction.response_description = result_desc
                transaction.raw_response = callback_data
                transaction.save()

                # Here you could trigger business logic like:
                # - Update property inquiry status
                # - Send confirmation emails
                # - Process the payment in your business logic

        return JsonResponse({'success': True})

    except Exception as e:
        # Log the error in production
        return JsonResponse({'error': str(e)}, status=500)
