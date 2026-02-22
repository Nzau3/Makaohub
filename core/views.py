from django.shortcuts import render
from django.conf import settings
from django.core.mail import send_mail
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from properties.models import Property, PropertyInquiry


def start_browsing(request):
    """Redirect users to an interface appropriate for their role.

    - Authenticated tenant -> tenant dashboard
    - Authenticated landlord -> landlord dashboard
    - Anonymous -> login page
    """
    user = request.user
    if not user.is_authenticated:
        return redirect('accounts:login')

    # Safely get role
    try:
        role = user.profile.role
    except Exception:
        role = 'tenant'

    if role == 'landlord':
        return redirect('accounts:landlord_dashboard')
    return redirect('accounts:tenant_dashboard')


def index(request):
    """Render the homepage."""
    return render(request, "core/home.html")


def about(request):
    """Render the about page."""
    return render(request, "core/about.html")


@require_http_methods(["GET", "POST"])
def contact(request):
    """Render and handle the contact / rental inquiry form.

    Supports property-specific inquiries (?property_id=<id>).
    Stores inquiries in PropertyInquiry model.
    Validates that tenants can only inquire about properties.
    """
    context = {}
    property_id = request.GET.get("property_id") or request.POST.get("property_id")
    property_obj = None

    # Try to load property if specified
    if property_id:
        try:
            property_obj = Property.objects.get(id=int(property_id))
        except (Property.DoesNotExist, ValueError):
            property_obj = None

    context["property"] = property_obj
    
    # Pre-fill form data if user is authenticated
    if request.user.is_authenticated:
        context["form"] = {
            "name": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
        }

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        message_text = request.POST.get("message", "").strip()

        # Role-based validation
        if request.user.is_authenticated:
            user_role = request.user.profile.role
            # Landlords should not submit inquiries about properties
            if user_role == 'landlord' and property_obj:
                context["error"] = "Landlords cannot submit inquiries about properties."
                return render(request, "core/contact.html", context)

        # Basic validation
        if not name or not email or not message_text:
            context["error"] = "Please provide your name, email, and a message."
            context["form"] = {
                "name": name,
                "email": email,
                "message": message_text,
            }
            return render(request, "core/contact.html", context)

        # Store inquiry in database if property is specified
        if property_obj:
            inquirer = request.user if request.user.is_authenticated else None
            inquirer_role = 'tenant'
            if inquirer:
                try:
                    inquirer_role = inquirer.profile.role
                except:
                    inquirer_role = 'tenant'

            try:
                PropertyInquiry.objects.create(
                    property=property_obj,
                    inquirer=inquirer,
                    inquirer_role=inquirer_role,
                    name=name,
                    email=email,
                    message=message_text,
                )
                context["success"] = True
                context["success_message"] = f"Your inquiry about {property_obj.title} has been sent to the landlord."
            except Exception as e:
                context["error"] = f"Error storing inquiry: {str(e)}"
                return render(request, "core/contact.html", context)
        else:
            # General inquiry (no property specified)
            try:
                default_from = getattr(settings, "DEFAULT_FROM_EMAIL", None)
                subject = f"MakaoHub inquiry from {name}"
                body_lines = [f"Name: {name}", f"Email: {email}", "", message_text]
                body = "\n".join(body_lines)

                if default_from:
                    send_mail(subject, body, default_from, [default_from], fail_silently=False)
                else:
                    print("[MakaoHub contact]", subject)
                    print(body)

                context["success"] = True
                context["success_message"] = "Thank you! Your message has been received."
            except Exception as exc:
                context["error"] = "There was an error sending your message. Please try again later."
                print("[MakaoHub contact] error:", exc)
                return render(request, "core/contact.html", context)

    return render(request, "core/contact.html", context)
