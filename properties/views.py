from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import get_user_role, landlord_required, tenant_required
from .forms import (
	MessageForm,
	PropertyFilterForm,
	PropertyForm,
	PropertyImageFormSet,
	PropertyInquiryForm,
)
from .models import Property, PropertyImage, PropertyInquiry
from .utils import mask_email, mask_phone


# Machakos Town approximate coordinates and key areas
MACHAKOS_LANDMARKS = {
	"machakos_cbd": {"lat": -1.5148, "lon": 37.6624, "name": "Machakos CBD"},
	"mikuyuni": {"lat": -1.5200, "lon": 37.6700, "name": "Mikuyuni"},
	"matungulu": {"lat": -1.5300, "lon": 37.6500, "name": "Matungulu"},
	"kangundo": {"lat": -1.5400, "lon": 37.6300, "name": "Kangundo"},
	"kiambu": {"lat": -1.5100, "lon": 37.6800, "name": "Kiambu"},
}


def property_list(request):
	"""Show rental properties with filters (neighborhood, type, price).

	Default view shows all available properties in Machakos.
	Students can filter by property type and price.
	Optional query param `student=1` prioritizes budget-friendly student rentals.
	"""
	from .models import SavedProperty
	
	form = PropertyFilterForm(request.GET)
	properties = Property.objects.available()
	
	# Get saved property IDs for the current user (if tenant)
	saved_property_ids = []
	if request.user.is_authenticated and hasattr(request.user, "profile") and request.user.profile.role == "tenant":
		saved_property_ids = list(SavedProperty.objects.filter(tenant=request.user).values_list('property_id', flat=True))

	# Apply filters from form (location-based: neighborhood and optional coordinates)
	if form.is_valid():
		neighborhood = form.cleaned_data.get("neighborhood")
		if neighborhood:
			properties = properties.filter(neighborhood=neighborhood)

		property_type = form.cleaned_data.get("property_type")
		if property_type:
			properties = properties.filter(property_type=property_type)

		min_price = form.cleaned_data.get("min_price")
		if min_price:
			properties = properties.filter(monthly_rent__gte=min_price)

		max_price = form.cleaned_data.get("max_price")
		if max_price:
			properties = properties.filter(monthly_rent__lte=max_price)

		search_query = form.cleaned_data.get("search_query")
		if search_query:
			properties = properties.filter(
				Q(title__icontains=search_query) | Q(location__icontains=search_query)
			)

		# Only show properties that have latitude/longitude (for map-based browsing)
		if form.cleaned_data.get("with_map_location"):
			properties = properties.filter(
				latitude__isnull=False,
				longitude__isnull=False,
			)

	# Student rentals in Machakos (budget-friendly defaults)
	student = request.GET.get("student") == "1"
	if student:
		properties = properties.filter(
			property_type__in=["bedsitter", "single_room", "hostel", "shared"],
			monthly_rent__lte=10000,  # Budget-friendly limit (approx USD 75)
		).order_by("monthly_rent")
	else:
		# Default ordering: recent listings first, then cheapest
		properties = properties.order_by("-created_at")

	# Map context for list (and future full-page map view at e.g. properties:map)
	map_context = {
		"center": {"lat": -1.5148, "lon": 37.6624},
		"landmarks": MACHAKOS_LANDMARKS,
		"properties": [
			{
				"id": p.id,
				"title": p.title,
				"lat": float(p.latitude) if p.latitude else None,
				"lon": float(p.longitude) if p.longitude else None,
				"rent": str(p.monthly_rent),
				"type": p.get_property_type_display(),
			}
			for p in properties
		],
	}

	# Pass Google Maps API key for optional list/map view (future: properties:map)
	google_maps_api_key = getattr(django_settings, "GOOGLE_MAPS_API_KEY", "") or ""

	context = {
		"properties": properties,
		"form": form,
		"student": student,
		"map_context": map_context,
		"saved_property_ids": saved_property_ids,
		"google_maps_api_key": google_maps_api_key,
	}

	return render(request, "properties/properties_list.html", context)


def properties_map_view(request):
	"""
	View all (filtered) properties on an interactive map (Phase 2).
	Uses same filters as listing; only properties with lat/lon are shown as markers.
	Tenant/public/landlord can view; no role restriction.
	"""
	form = PropertyFilterForm(request.GET)
	properties = Property.objects.available()

	# Apply same filters as property_list (neighborhood, type, price, search, with_map_location)
	if form.is_valid():
		neighborhood = form.cleaned_data.get("neighborhood")
		if neighborhood:
			properties = properties.filter(neighborhood=neighborhood)
		property_type = form.cleaned_data.get("property_type")
		if property_type:
			properties = properties.filter(property_type=property_type)
		min_price = form.cleaned_data.get("min_price")
		if min_price:
			properties = properties.filter(monthly_rent__gte=min_price)
		max_price = form.cleaned_data.get("max_price")
		if max_price:
			properties = properties.filter(monthly_rent__lte=max_price)
		search_query = form.cleaned_data.get("search_query")
		if search_query:
			properties = properties.filter(
				Q(title__icontains=search_query) | Q(location__icontains=search_query)
			)
		if form.cleaned_data.get("with_map_location"):
			properties = properties.filter(
				latitude__isnull=False,
				longitude__isnull=False,
			)

	# Preset budget (student=1)
	student = request.GET.get("student") == "1"
	if student:
		properties = properties.filter(
			property_type__in=["bedsitter", "single_room", "hostel", "shared"],
			monthly_rent__lte=10000,
		).order_by("monthly_rent")
	else:
		properties = properties.order_by("-created_at")

	# Map view: only show markers for properties with coordinates (required for placing pins)
	properties_with_coords = properties.filter(
		latitude__isnull=False,
		longitude__isnull=False,
	)

	# Build marker list for template (popup: title, neighborhood, link to detail)
	markers = [
		{
			"id": p.id,
			"title": p.title,
			"lat": float(p.latitude),
			"lon": float(p.longitude),
			"neighborhood": p.get_neighborhood_display(),
			"detail_url": reverse("properties:detail", kwargs={"id": p.id}),
		}
		for p in properties_with_coords
	]

	google_maps_api_key = getattr(django_settings, "GOOGLE_MAPS_API_KEY", "") or ""

	context = {
		"form": form,
		"student": student,
		"markers": markers,
		"google_maps_api_key": google_maps_api_key,
	}
	return render(request, "properties/properties_map.html", context)


def property_detail(request, id):
	"""Show a single rental property with images and location data."""
	from .models import SavedProperty

	prop = get_object_or_404(Property, id=id)
	images = prop.images.all()

	# Check if property is saved by current user
	is_saved = False
	if request.user.is_authenticated and hasattr(request.user, "profile") and request.user.profile.role == "tenant":
		is_saved = SavedProperty.objects.filter(tenant=request.user, property=prop).exists()

	# Google Maps API key: when set, detail template shows small Google Maps preview (Leaflet kept as-is)
	google_maps_api_key = getattr(django_settings, "GOOGLE_MAPS_API_KEY", "") or ""

	return render(
		request,
		"properties/property_detail.html",
		{
			"property": prop,
			"images": images,
			"is_saved": is_saved,
			"google_maps_api_key": google_maps_api_key,
			"masked_landlord_email": mask_email(prop.landlord.email),
		},
	)


@login_required
@landlord_required
def property_create(request):
    """Allow landlords to add a rental property. Images and optional video via form/formset."""
    if request.method == "POST":
        form = PropertyForm(request.POST, request.FILES)
        if form.is_valid():
            prop = form.save(commit=False)
            prop.landlord = request.user
            prop.save()
            formset = PropertyImageFormSet(request.POST, request.FILES, instance=prop)
            if formset.is_valid():
                formset.save()
                messages.success(request, "Property created successfully.")
                return redirect("properties:detail", id=prop.id)
            else:
                # If images invalid, render form with errors
                messages.warning(request, "Property saved but images had errors.")
        else:
            formset = PropertyImageFormSet(request.POST, request.FILES)
    else:
        form = PropertyForm()
        # Provide empty formset for up to 3 images
        formset = PropertyImageFormSet(instance=Property())

    # Pass Google Maps API key for optional reverse geocoding (neighborhood) in form template
    google_maps_api_key = getattr(django_settings, "GOOGLE_MAPS_API_KEY", "") or ""
    return render(request, "properties/property_form.html", {
        "form": form,
        "formset": formset,
        "google_maps_api_key": google_maps_api_key,
    })


@login_required
@landlord_required
def my_properties(request):
    """Show properties added by the logged-in landlord."""
    properties = Property.objects.filter(landlord=request.user)
    return render(request, "properties/my_properties.html", {"properties": properties})


@login_required
@landlord_required
def property_update(request, id):
	"""Update an existing property. Only landlord who owns the property can edit."""
	prop = get_object_or_404(Property, id=id)
	
	# Strict ownership check: only the landlord who created the property can edit
	if prop.landlord != request.user:
		messages.error(request, "You do not have permission to edit this property.")
		return redirect("properties:detail", id=prop.id)
	
	if request.method == "POST":
		form = PropertyForm(request.POST, request.FILES, instance=prop)
		if form.is_valid():
			prop = form.save()
			# Update images if provided
			formset = PropertyImageFormSet(request.POST, request.FILES, instance=prop)
			if formset.is_valid():
				formset.save()
				messages.success(request, "Property updated successfully.")
				return redirect("properties:detail", id=prop.id)
			else:
				messages.warning(request, "Property updated but images had errors.")
		else:
			messages.error(request, "Please correct the errors below.")
	else:
		form = PropertyForm(instance=prop)
		formset = PropertyImageFormSet(instance=prop)
	
	# Pass Google Maps API key for optional reverse geocoding (neighborhood) in form template
	google_maps_api_key = getattr(django_settings, "GOOGLE_MAPS_API_KEY", "") or ""
	context = {
		"form": form,
		"formset": formset,
		"property": prop,
		"is_edit": True,
		"google_maps_api_key": google_maps_api_key,
	}
	return render(request, "properties/property_form.html", context)


@login_required
@landlord_required
def property_delete(request, id):
	"""Delete a property. Only landlord who owns the property can delete."""
	prop = get_object_or_404(Property, id=id)
	
	# Strict ownership check
	if prop.landlord != request.user:
		messages.error(request, "You do not have permission to delete this property.")
		return redirect("properties:detail", id=prop.id)
	
	if request.method == "POST":
		prop.delete()
		messages.success(request, "Property deleted successfully.")
		return redirect("properties:my_properties")
	
	# GET request: show confirmation page
	return render(request, "properties/property_delete_confirm.html", {"property": prop})


@login_required
@tenant_required
def saved_properties(request):
	"""List all properties saved by the logged-in tenant."""
	from .models import SavedProperty
	
	saved_props = SavedProperty.objects.filter(tenant=request.user).select_related('property')
	properties = [sp.property for sp in saved_props]
	
	context = {
		"properties": properties,
		"saved_count": saved_props.count(),
	}
	return render(request, "properties/saved_properties.html", context)


@login_required
@tenant_required
def save_property(request, id):
	"""Save a property for the logged-in tenant."""
	from .models import SavedProperty
	
	prop = get_object_or_404(Property, id=id)

	# Enforce POST-only to avoid accidental saves via GET
	if request.method != "POST":
		messages.error(request, "Invalid request method for saving a property.")
		return redirect("properties:detail", id=id)
	
	# Check if already saved
	saved, created = SavedProperty.objects.get_or_create(
		tenant=request.user,
		property=prop
	)
	
	if created:
		messages.success(request, f"Property '{prop.title}' saved to your favorites.")
	else:
		messages.info(request, f"Property '{prop.title}' is already in your favorites.")
	
	return redirect("properties:detail", id=id)


@login_required
@tenant_required
def unsave_property(request, id):
	"""Remove a property from saved list."""
	from .models import SavedProperty
	
	prop = get_object_or_404(Property, id=id)

	# Enforce POST-only to avoid accidental changes via GET
	if request.method != "POST":
		messages.error(request, "Invalid request method for removing a saved property.")
		return redirect("properties:detail", id=id)
	
	try:
		saved = SavedProperty.objects.get(tenant=request.user, property=prop)
		saved.delete()
		messages.success(request, f"Property '{prop.title}' removed from your favorites.")
	except SavedProperty.DoesNotExist:
		messages.info(request, "Property was not in your saved list.")
	
	return redirect("properties:detail", id=id)


@login_required
@landlord_required
def property_inquiries(request):
	"""List all inquiries for properties owned by the logged-in landlord."""
	from properties.models import PropertyInquiry
	
	# Get all properties owned by this landlord
	landlord_properties = Property.objects.filter(landlord=request.user)
	
	# Get all inquiries for these properties
	inquiries = PropertyInquiry.objects.filter(
		property__in=landlord_properties
	).select_related('property', 'inquirer').order_by('-created_at')
	
	# Count by status
	pending_count = inquiries.filter(status='pending').count()
	responded_count = inquiries.filter(status='responded').count()
	total_count = inquiries.count()
	
	context = {
		"inquiries": inquiries,
		"pending_count": pending_count,
		"responded_count": responded_count,
		"total_count": total_count,
	}
	return render(request, "properties/inquiries_list.html", context)


@login_required
@login_required
def inquiry_detail(request, id):
	"""
	View inquiry details with threaded messages (Phase 1).
	Access: tenant who sent the inquiry OR landlord who owns the property.
	Handles both status updates (landlord) and new messages (tenant/landlord).
	"""
	from properties.models import Message, PropertyInquiry
	from django.http import HttpResponseForbidden
	
	inquiry = get_object_or_404(PropertyInquiry, id=id)
	
	# Access control: only tenant who sent inquiry OR landlord who owns property
	is_tenant = request.user == inquiry.tenant
	is_landlord = request.user == inquiry.property.landlord
	
	if not (is_tenant or is_landlord):
		return HttpResponseForbidden("You do not have permission to view this inquiry.")
	
	# Get all messages for this inquiry (chronological)
	thread_messages = Message.objects.filter(inquiry=inquiry).select_related("sender").order_by("created_at")
	
	# Handle POST: status update (landlord) or new message (tenant/landlord)
	if request.method == "POST":
		# Check if this is a status update (landlord only)
		if "status" in request.POST and is_landlord:
			new_status = request.POST.get("status")
			if new_status in ['pending', 'responded', 'closed']:
				inquiry.status = new_status
				inquiry.save()
				messages.success(request, f"Inquiry status updated to {new_status}.")
				return redirect("properties:inquiry_detail", id=id)
		
		# Otherwise, handle new message (tenant or landlord)
		message_form = MessageForm(request.POST)
		if message_form.is_valid():
			# Determine receiver
			if request.user == inquiry.tenant:
				receiver = inquiry.property.landlord
			else:
				receiver = inquiry.tenant
			Message.objects.create(
				inquiry=inquiry,
				sender=request.user,
				receiver=receiver,
				body=message_form.cleaned_data["body"],
			)
			
			# Update inquiry status based on sender (only if not closed)
			if inquiry.status != 'closed':
				if is_landlord:
					inquiry.status = "responded"
				elif is_tenant:
					inquiry.status = "pending"
				inquiry.save()
			
			messages.success(request, "Your message has been sent.")
			return redirect("properties:inquiry_detail", id=id)
		else:
			# Form errors will be shown in template
			pass
	else:
		message_form = MessageForm()
	
	context = {
		"inquiry": inquiry,
		"thread_messages": thread_messages,
		"message_form": message_form,
		"is_tenant": is_tenant,
		"is_landlord": is_landlord,
		"masked_email": mask_email(inquiry.email),
	}
	return render(request, "properties/inquiry_detail.html", context)


@login_required
def inquiry_conversation(request, inquiry_id):
	"""
	WhatsApp-style conversation view for a PropertyInquiry.
	Accessible only to the tenant who sent the inquiry or the landlord who owns the property.
	Handles GET (display conversation) and POST (send message).
	When landlord sends a message, automatically set inquiry.status to 'responded'.
	"""
	from properties.models import Message, PropertyInquiry
	from django.http import HttpResponseForbidden
	
	inquiry = get_object_or_404(PropertyInquiry, id=inquiry_id)
	
	# Access control: only tenant who sent inquiry OR landlord who owns property
	is_tenant = request.user == inquiry.tenant
	is_landlord = request.user == inquiry.property.landlord
	
	if not (is_tenant or is_landlord):
		return HttpResponseForbidden("You do not have permission to view this conversation.")
	
	# Get all messages for this inquiry (chronological)
	messages_list = Message.objects.filter(inquiry=inquiry).select_related("sender", "receiver").order_by("created_at")

	# Handle POST: create new message
	if request.method == "POST":
		body = request.POST.get("body", "").strip()
		if body:
			# Determine receiver
			if request.user == inquiry.tenant:
				receiver = inquiry.property.landlord
			else:
				receiver = inquiry.tenant
			msg = Message.objects.create(
				inquiry=inquiry,
				sender=request.user,
				receiver=receiver,
				body=body,
			)

			# Update inquiry status automatically on reply (only if not closed)
			if inquiry.status != 'closed':
				inquiry.status = "responded"
				inquiry.save()

			messages.success(request, "Message sent.")
			return redirect("properties:inquiry_conversation", inquiry_id=inquiry_id)

	context = {
		"inquiry": inquiry,
		"messages_list": messages_list,
		"is_tenant": is_tenant,
		"is_landlord": is_landlord,
		"masked_email": mask_email(inquiry.email),
	}
	return render(request, "properties/inquiry_conversation.html", context)


@login_required
@tenant_required
def send_inquiry(request, property_id):
	"""Allow tenants to send an inquiry to a property's landlord."""
	from .models import Message
	
	prop = get_object_or_404(Property, id=property_id)

	if request.method == "POST":
		form = PropertyInquiryForm(request.POST)
		if form.is_valid():
			# Create the inquiry
			inquiry = PropertyInquiry.objects.create(
				property=prop,
				tenant=request.user,
				inquirer=request.user,
				inquirer_role="tenant",
				name=request.user.get_full_name() or request.user.username,
				email=request.user.email,
				message=form.cleaned_data["message"],
			)

			# Create the initial message in the conversation thread
			Message.objects.create(
				inquiry=inquiry,
				sender=request.user,
				receiver=prop.landlord,
				body=form.cleaned_data["message"],
			)

			# Set inquiry status to 'pending' (explicit)
			inquiry.status = 'pending'
			inquiry.save()

			messages.success(request, "Your inquiry has been sent to the landlord.")
			return redirect("properties:tenant_inbox")
	else:
		form = PropertyInquiryForm()

	return render(
		request,
		"properties/inquiry_form.html",
		{
			"form": form,
			"property": prop,
		},
	)


@login_required
@tenant_required
def tenant_inbox(request):
	"""
	Tenant Inbox: Shows all inquiries with messages where the tenant is involved.
	Displays property title, landlord name, last message preview, status, and last updated.
	"""
	from properties.models import Message, PropertyInquiry
	
	# Get all inquiries where current user is the tenant
	inquiries = PropertyInquiry.objects.filter(
		tenant=request.user
	).select_related(
		'property__landlord', 'tenant'
	).prefetch_related(
		'messages'
	).order_by('-updated_at')
	
	# Add last message info to each inquiry
	inbox_items = []
	for inquiry in inquiries:
		last_message = inquiry.messages.order_by('-created_at').first()
		inbox_items.append({
			'inquiry': inquiry,
			'last_message': last_message,
			'has_unread': inquiry.messages.filter(receiver=request.user, is_read=False).exists(),
		})

	context = {
		'inbox_items': inbox_items,
	}
	return render(request, "properties/tenant_inbox.html", context)


@login_required
@landlord_required
def landlord_inbox(request):
	"""
	Landlord Inbox: Shows all inquiries with messages for properties owned by the landlord.
	Displays property title, tenant name, last message preview, status, and last updated.
	"""
	from properties.models import Message, PropertyInquiry
	
	# Get all inquiries for properties owned by current user
	inquiries = PropertyInquiry.objects.filter(
		property__landlord=request.user
	).select_related(
		'property__landlord', 'tenant'
	).prefetch_related(
		'messages'
	).order_by('-updated_at')
	
	# Add last message info to each inquiry
	inbox_items = []
	for inquiry in inquiries:
		last_message = inquiry.messages.order_by('-created_at').first()
		inbox_items.append({
			'inquiry': inquiry,
			'last_message': last_message,
			'has_unread': inquiry.messages.filter(receiver=request.user, is_read=False).exists(),
		})

	context = {
		'inbox_items': inbox_items,
	}
	return render(request, "properties/landlord_inbox.html", context)


@login_required
@landlord_required
def landlord_inquiries(request):
	"""Display all inquiries for properties owned by the logged-in landlord."""
	inquiries = (
		PropertyInquiry.objects.filter(property__landlord=request.user)
		.select_related("property", "tenant")
		.order_by("-created_at")
	)

	# Mark all as read when viewed
	inquiries.filter(is_read=False).update(is_read=True)

	return render(
		request,
		"properties/landlord_inquiries.html",
		{
			"inquiries": inquiries,
		},
	)