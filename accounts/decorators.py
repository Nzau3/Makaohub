from functools import wraps

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def get_user_role(user):
    """
    Safely get the user's role, ensuring a Profile exists and
    defaulting to 'tenant' if anything is missing.
    """
    from accounts.models import Profile

    try:
        profile, _ = Profile.objects.get_or_create(user=user)
        # Normalize empty/invalid role values to a safe default
        role = profile.role or 'tenant'
        if profile.role != role:
            profile.role = role
            profile.save(update_fields=["role"])
        return role
    except Exception:
        # In the worst case, treat user as a tenant rather than erroring
        return "tenant"


def landlord_required(view_func):
    """
    Decorator to restrict access to landlord users only.

    - Unauthenticated users are redirected to login.
    - Authenticated users receive HTTP 403 only when their role is not 'landlord'.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect("accounts:login")

        role = get_user_role(user)
        if role == "landlord":
            return view_func(request, *args, **kwargs)

        # Role is present but does not match the required one -> 403
        messages.warning(request, "You don't have permission to access landlord features.")
        return HttpResponseForbidden("Landlord access required.")

    return wrapper


def tenant_required(view_func):
    """
    Decorator to restrict access to tenant users only.

    - Unauthenticated users are redirected to login.
    - Authenticated users receive HTTP 403 only when their role is not 'tenant'.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect("accounts:login")

        role = get_user_role(user)
        if role == "tenant":
            return view_func(request, *args, **kwargs)

        # Role is present but does not match the required one -> 403
        messages.warning(request, "You don't have permission to access tenant-only features.")
        return HttpResponseForbidden("Tenant access required.")

    return wrapper


def is_landlord(user):
    """Check if user is a landlord."""
    return user.is_authenticated and get_user_role(user) == "landlord"


def is_tenant(user):
    """Check if user is a tenant."""
    return user.is_authenticated and get_user_role(user) == "tenant"
