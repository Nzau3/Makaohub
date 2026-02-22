from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


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