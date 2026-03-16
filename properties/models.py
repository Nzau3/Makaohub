from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def has_paid_rent(allocation: "TenantAllocation") -> bool:
	"""
	Return True if the tenant has a successful rent payment for this allocation
	in the current month.
	"""
	today = date.today()
	return RentPayment.objects.filter(
		allocation=allocation,
		tenant=allocation.tenant,
		status=RentPayment.Status.SUCCESSFUL,
		created_at__year=today.year,
		created_at__month=today.month,
	).exists()


class TenantAllocation(models.Model):
	"""
	Represents a tenancy relationship between a tenant and a property.
	Landlord must match the property's owner.
	"""

	class Status(models.TextChoices):
		ACTIVE = "active", _("Active")
		ENDED = "ended", _("Ended")

	tenant = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="allocations",
	)
	property = models.ForeignKey(
		"Property",
		on_delete=models.CASCADE,
		related_name="allocations",
	)
	landlord = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="tenant_allocations_as_landlord",
	)
	room_number = models.CharField(max_length=20, blank=True, null=True)
	rent_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
	start_date = models.DateField(default=timezone.localdate)
	end_date = models.DateField(blank=True, null=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
	created_at = models.DateTimeField(default=timezone.now, editable=False)

	class Meta:
		ordering = ["-start_date"]
		constraints = [
			models.UniqueConstraint(
				fields=["tenant", "property"],
				condition=Q(status="active"),
				name="uniq_active_allocation_per_tenant_property",
			),
		]

	def clean(self):
		super().clean()
		if not self.property_id:
			return

		# Always enforce landlord + rent from the property (read-only fields)
		expected_landlord_id = self.property.landlord_id
		expected_rent = self.property.monthly_rent

		if self.landlord_id and self.landlord_id != expected_landlord_id:
			raise ValidationError({"landlord": "Landlord must match the property's owner."})

		if self.rent_amount and self.rent_amount != expected_rent:
			raise ValidationError({"rent_amount": "Rent must match the property's monthly rent."})

	def save(self, *args, **kwargs):
		# Always derive these fields server-side to prevent tampering.
		if self.property_id:
			self.landlord_id = self.property.landlord_id
			self.rent_amount = self.property.monthly_rent

		self.full_clean()
		return super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.tenant} -> {self.property} ({self.status})"


class RentPayment(models.Model):
	"""
	Rent payments are always linked to a TenantAllocation (not directly to Property).
	Amount is derived from allocation.rent_amount.
	"""

	class Status(models.TextChoices):
		PENDING = "pending", _("Pending")
		SUCCESSFUL = "successful", _("Successful")
		FAILED = "failed", _("Failed")

	class Method(models.TextChoices):
		MPESA = "mpesa", _("M-Pesa")
		CASH = "cash", _("Cash")
		OTHER = "other", _("Other")

	tenant = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="rent_payments",
	)
	allocation = models.ForeignKey(
		TenantAllocation,
		on_delete=models.CASCADE,
		related_name="rent_payments",
	)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	payment_method = models.CharField(max_length=20, choices=Method.choices, default=Method.MPESA)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)
	payment_date = models.DateTimeField(blank=True, null=True)
	created_at = models.DateTimeField(default=timezone.now, editable=False)

	class Meta:
		ordering = ["-created_at"]

	def clean(self):
		super().clean()
		if self.allocation_id:
			if self.tenant_id and self.tenant_id != self.allocation.tenant_id:
				raise ValidationError({"tenant": "Tenant must match allocation.tenant."})
			if self.allocation.status != TenantAllocation.Status.ACTIVE:
				raise ValidationError({"allocation": "Tenant must have an active allocation before paying rent."})

			# Always derive amount from allocation
			if self.amount != self.allocation.rent_amount:
				self.amount = self.allocation.rent_amount

			# Prevent duplicate payments for same allocation in same month (pending/successful)
			month_anchor = self.payment_date or timezone.now()
			start = month_anchor.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
			end = (start + timedelta(days=32)).replace(day=1)
			exists = (
				RentPayment.objects.filter(
					allocation=self.allocation,
					tenant=self.allocation.tenant,
					created_at__gte=start,
					created_at__lt=end,
				)
				.exclude(pk=self.pk)
				.exclude(status=RentPayment.Status.FAILED)
				.exists()
			)
			if exists:
				raise ValidationError("Duplicate rent payment for this month is not allowed.")

	def save(self, *args, **kwargs):
		if self.allocation_id:
			self.tenant_id = self.allocation.tenant_id
			self.amount = self.allocation.rent_amount
			if self.status == RentPayment.Status.SUCCESSFUL and not self.payment_date:
				self.payment_date = timezone.now()
		self.full_clean()
		return super().save(*args, **kwargs)

	def __str__(self):
		return f"RentPayment({self.tenant} / {self.allocation_id} / {self.status})"


class ContactPayment(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", _("Pending")
		SUCCESSFUL = "successful", _("Successful")

	tenant = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contact_payments"
	)
	property = models.ForeignKey("Property", on_delete=models.CASCADE, related_name="contact_payments")
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	transaction_id = models.CharField(max_length=100, blank=True, null=True)
	created_at = models.DateTimeField(default=timezone.now, editable=False)

	class Meta:
		ordering = ["-created_at"]


class FeaturedPayment(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", _("Pending")
		SUCCESSFUL = "successful", _("Successful")
		FAILED = "failed", _("Failed")

	landlord = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="featured_payments"
	)
	property = models.ForeignKey("Property", on_delete=models.CASCADE, related_name="featured_payments")
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	transaction_id = models.CharField(max_length=100, blank=True, null=True)
	featured_until = models.DateTimeField(blank=True, null=True)
	created_at = models.DateTimeField(default=timezone.now, editable=False)

	class Meta:
		ordering = ["-created_at"]

	def clean(self):
		super().clean()
		if self.property_id and self.landlord_id and self.property.landlord_id != self.landlord_id:
			raise ValidationError({"property": "Property must belong to the landlord."})


class PropertyQuerySet(models.QuerySet):
	def available(self):
		"""Return only available rental properties."""
		return self.filter(is_available=True)

	def in_machakos(self):
		"""Return properties whose location mentions Machakos (simple filter).

		This is a lightweight text match to support the initial scope (Machakos Town).
		For more accurate results, store structured city fields or use geocoding.
		"""
		return self.filter(location__icontains="Machakos")

	def student_rentals_in_machakos(self):
		"""Return available property types that are student-friendly in Machakos Town."""
		student_types = [
			"bedsitter",
			"single_room",
			"hostel",
			"shared",
		]
		return (
			self.available()
			.in_machakos()
			.filter(property_type__in=student_types)
		)


class PropertyManager(models.Manager):
	def get_queryset(self):
		return PropertyQuerySet(self.model, using=self._db)

	def available(self):
		return self.get_queryset().available()

	def student_rentals_in_machakos(self):
		return self.get_queryset().student_rentals_in_machakos()


class Property(models.Model):
	class PropertyType(models.TextChoices):
		BEDSITTER = "bedsitter", _("Bedsitter")
		SINGLE_ROOM = "single_room", _("Single room")
		ONE_BEDROOM = "one_bedroom", _("1-bedroom")
		HOSTEL = "hostel", _("Hostel")
		SHARED = "shared", _("Shared")

	class Neighborhood(models.TextChoices):
		MACHAKOS_CBD = "machakos_cbd", _("Machakos CBD")
		MIKUYUNI = "mikuyuni", _("Mikuyuni")
		MATUNGULU = "matungulu", _("Matungulu")
		KANGUNDO = "kangundo", _("Kangundo")
		KIAMBU = "kiambu", _("Kiambu")
		OTHER = "other", _("Other")

	landlord = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="properties",
		help_text=_("The landlord (owner) who listed this property."),
	)
	title = models.CharField(max_length=200)
	property_type = models.CharField(
		max_length=32, choices=PropertyType.choices, default=PropertyType.BEDSITTER
	)
	location = models.CharField(
		max_length=255,
		help_text=_("Address or description of where the property is located (e.g. Machakos Town)."),
	)
	neighborhood = models.CharField(
		max_length=32,
		choices=Neighborhood.choices,
		default=Neighborhood.MACHAKOS_CBD,
		help_text=_("Neighborhood or area in Machakos."),
	)
	nearby_shopping_center = models.CharField(
		max_length=255,
		blank=True,
		help_text=_("Nearest shopping center or landmark."),
	)
	monthly_rent = models.DecimalField(
		max_digits=10, decimal_places=2, help_text=_("Monthly rent in Kenyan Shillings (KES).")
	)
	description = models.TextField(blank=True)
	is_available = models.BooleanField(default=True)
	# Featured listing fields
	is_featured = models.BooleanField(default=False)
	featured_until = models.DateTimeField(null=True, blank=True)
	# Optional fields to support map integration (latitude/longitude)
	latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	# Optional short video (landlord upload); served via MEDIA_URL in dev
	video = models.FileField(
		upload_to="property_videos/",
		blank=True,
		null=True,
		help_text=_("Upload a short video of the property (optional)."),
	)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	objects = PropertyManager()

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.title} — {self.location} ({self.get_property_type_display()})"

	def save(self, *args, **kwargs):
		from django.utils import timezone
		if self.is_featured and self.featured_until:
			if self.featured_until < timezone.now():
				self.is_featured = False
		super().save(*args, **kwargs)


class PropertyImage(models.Model):
	property = models.ForeignKey(
		Property, on_delete=models.CASCADE, related_name="images"
	)
	image = models.ImageField(upload_to="property_images/")
	caption = models.CharField(max_length=255, blank=True)
	uploaded_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Image for {self.property.title} ({self.id})"


class PropertyInquiry(models.Model):
	"""Track inquiries/applications from tenants about properties."""
	
	INQUIRY_STATUS_CHOICES = (
		('pending', 'Pending'),
		('responded', 'Responded'),
		('closed', 'Closed'),
	)
	
	property = models.ForeignKey(
		Property, on_delete=models.CASCADE, related_name="inquiries"
	)
	tenant = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="property_inquiries",
		help_text=_("Tenant who submitted the inquiry."),
	)
	inquirer = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="inquiries",
		help_text=_("User who submitted the inquiry (should be a tenant)."),
		null=True,
		blank=True,
	)
	inquirer_role = models.CharField(
		max_length=20,
		choices=[('tenant', 'Tenant'), ('landlord', 'Landlord')],
		help_text=_("Role of inquirer at time of submission."),
		null=True,
		blank=True,
	)
	name = models.CharField(max_length=200, blank=True, default="")
	email = models.EmailField(blank=True, default="")
	message = models.TextField()
	is_read = models.BooleanField(default=False)
	status = models.CharField(
		max_length=20,
		choices=INQUIRY_STATUS_CHOICES,
		default='pending',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		ordering = ["-created_at"]
	
	def __str__(self):
		return f"Inquiry from {self.name} about {self.property.title}"


class SavedProperty(models.Model):
	"""Allow tenants to save/favorite properties for later viewing."""
	
	tenant = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="saved_properties",
		help_text=_("Tenant who saved this property."),
	)
	property = models.ForeignKey(
		Property,
		on_delete=models.CASCADE,
		related_name="saved_by",
		help_text=_("Property that was saved."),
	)
	saved_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		unique_together = [['tenant', 'property']]
		ordering = ["-saved_at"]
	
	def __str__(self):
		return f"{self.tenant.username} saved {self.property.title}"


class Message(models.Model):
	"""
	Threaded messages for PropertyInquiry conversations (Phase 1: non-real-time).
	Each PropertyInquiry can have multiple Message replies.
	Only the tenant who sent the inquiry and the property's landlord can view/send messages.
	"""
	inquiry = models.ForeignKey(
		PropertyInquiry,
		on_delete=models.CASCADE,
		related_name="messages",
		help_text=_("The inquiry this message belongs to."),
	)
	sender = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="sent_messages",
		help_text=_("User who sent this message (tenant or landlord)."),
	)
	receiver = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="received_messages",
		help_text=_("User who receives this message (tenant or landlord)."),
    null=True,
    blank=True
)
	body = models.TextField(
		help_text=_("Message content."),
	)
	is_read = models.BooleanField(
		default=False,
		help_text=_("Mark as read for future notification features."),
	)
	created_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		ordering = ["created_at"]
	
	def __str__(self):
		return f"Message from {self.sender.username} on inquiry #{self.inquiry.id}"