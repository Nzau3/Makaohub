from .decorators import tenant_required, landlord_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
@login_required
@tenant_required
@require_POST
def simulate_rent_payment(request, property_id):
    """
    Placeholder endpoint for future rent payments.
    Real M-Pesa integration will be added later.
    """
    return JsonResponse(
        {
            "success": False,
            "message": "Payment integration coming soon. M-Pesa payments will be enabled soon.",
        },
        status=200,
    )


from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render

from .decorators import get_user_role, landlord_required, tenant_required
from .forms import RoleBasedUserCreationForm, ProfileUpdateForm


def get_role_redirect_url(user):
    """Return the appropriate dashboard URL based on user role."""
    role = get_user_role(user)
    return "accounts:landlord_dashboard" if role == "landlord" else "accounts:tenant_dashboard"


def register(request):
    """Handle user registration with role selection."""
    if request.method == "POST":
        form = RoleBasedUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            role = user.profile.role
            messages.success(request, f"Registration successful. Welcome, {role}!")
            return redirect("accounts:role_redirect")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RoleBasedUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    """Authenticate and log in users using Django's AuthenticationForm."""
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Ensure Profile exists for user
            from .models import Profile
            Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_username()}!")
            # Check for next_url, otherwise redirect based on role
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("accounts:role_redirect")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm(request)

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Log out the user and redirect to home."""
    logout(request)
    messages.info(request, "You have been signed out.")
    # Redirect to the project's homepage using the core namespace
    return redirect("core:index")


@login_required
def dashboard(request):
    """Render the user dashboard."""
    return render(request, "accounts/dashboard.html")


@login_required
def profile_edit(request):
    """Simple profile edit view to update basic user info."""
    user = request.user
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:dashboard")

    return render(request, "accounts/profile_edit.html", {"user": user})


@login_required
def profile_update(request):
    """Update profile with phone number and validation."""
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your mobile number was updated successfully.")
            return redirect("accounts:profile_update")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
@tenant_required
def tenant_dashboard(request):
    """Dashboard for tenant users."""
    from properties.models import SavedProperty, TenantAllocation, has_paid_rent, RentPayment

    user = request.user
    saved_qs = SavedProperty.objects.filter(tenant=user).select_related("property")
    saved_properties = [sp.property for sp in saved_qs]
    saved_count = len(saved_properties)

    allocation = TenantAllocation.objects.filter(tenant=user, status=TenantAllocation.Status.ACTIVE).select_related("property").first()
    paid = False
    last_payment = None
    if allocation:
        paid = has_paid_rent(allocation)
        last_payment = (
            RentPayment.objects.filter(
                tenant=user,
                allocation=allocation,
                status=RentPayment.Status.SUCCESSFUL,
            )
            .order_by("-payment_date", "-created_at")
            .first()
        )

    context = {
        "user": user,
        "role": "tenant",
        "saved_properties_count": saved_count,
        "saved_properties": saved_properties,
        "allocation": allocation,
        "paid": paid,
        "last_payment": last_payment,
    }
    return render(request, "accounts/tenant_dashboard.html", context)


@login_required
@landlord_required
def landlord_dashboard(request):
    """Dashboard for landlord users."""
    from properties.models import Property, PropertyInquiry, RentPayment, TenantAllocation, has_paid_rent

    user = request.user
    properties = Property.objects.filter(landlord=user)
    inquiries = PropertyInquiry.objects.filter(property__landlord=user)

    # For each property, get allocations and payment info
    property_allocations = []
    for prop in properties:
        allocations = prop.allocations.filter(status=TenantAllocation.Status.ACTIVE).select_related("tenant")
        allocation_rows = []
        for alloc in allocations:
            paid = has_paid_rent(alloc)
            last_payment = (
                RentPayment.objects.filter(
                    tenant=alloc.tenant,
                    allocation=alloc,
                    status=RentPayment.Status.SUCCESSFUL,
                )
                .order_by("-payment_date", "-created_at")
                .first()
            )
            allocation_rows.append({
                'tenant': alloc.tenant,
                'room_number': alloc.room_number,
                'rent_amount': alloc.rent_amount,
                'paid': paid,
                'last_payment': last_payment,
            })
        property_allocations.append({
            'property': prop,
            'allocations': allocation_rows,
        })

    context = {
        'user': user,
        'role': 'landlord',
        'total_properties': properties.count(),
        'active_listings': properties.filter(is_available=True).count(),
        'total_inquiries': inquiries.count(),
        'pending_inquiries': inquiries.filter(status='pending').count(),
        'property_allocations': property_allocations,
    }
    return render(request, "accounts/landlord_dashboard.html", context)


@login_required
def role_redirect(request):
    """Neutral post-login router that sends users to their role dashboard based on profile role."""
    redirect_name = get_role_redirect_url(request.user)
    return redirect(redirect_name)


def start_browsing(request):
    """Redirect users to the appropriate interface based on role.

    - Anonymous -> accounts:login
    - Authenticated tenant -> accounts:tenant_dashboard
    - Authenticated landlord -> accounts:landlord_dashboard
    """
    user = request.user
    if not user.is_authenticated:
        return redirect("accounts:login")

    role = get_user_role(user)
    if role == "landlord":
        return redirect("accounts:landlord_dashboard")
    return redirect("accounts:tenant_dashboard")
