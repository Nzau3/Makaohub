from django import forms

from .models import PropertyInquiry


class PropertyInquiryForm(forms.ModelForm):
	class Meta:
		model = PropertyInquiry
		fields = ["message"]
		widgets = {
			"message": forms.Textarea(
				attrs={
					"rows": 4,
					"placeholder": "Write your message here...",
					"class": "form-control",
				}
			)
		}
from django import forms
from django.forms import inlineformset_factory

from .models import Property, PropertyImage, PropertyInquiry
from .models import TenantAllocation
from django.contrib.auth import get_user_model

User = get_user_model()


class PropertyFilterForm(forms.Form):
	"""Filter form for searching properties by neighborhood, type, and price range."""
	neighborhood = forms.ChoiceField(
		choices=[("", "All Neighborhoods")] + list(Property.Neighborhood.choices),
		required=False,
		label="Neighborhood",
		widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
	)
	property_type = forms.ChoiceField(
		choices=[("", "All Types")] + list(Property.PropertyType.choices),
		required=False,
		label="Property Type",
		widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
	)
	min_price = forms.DecimalField(
		required=False,
		label="Min Monthly Rent (KES)",
		widget=forms.NumberInput(attrs={"class": "form-control form-control-sm", "placeholder": "e.g. 1000"}),
	)
	max_price = forms.DecimalField(
		required=False,
		label="Max Monthly Rent (KES)",
		widget=forms.NumberInput(attrs={"class": "form-control form-control-sm", "placeholder": "e.g. 10000"}),
	)
	search_query = forms.CharField(
		required=False,
		label="Search",
		widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Search by title or location..."}),
	)
	# Location-based: only show properties that have map coordinates (for future map view)
	with_map_location = forms.BooleanField(
		required=False,
		label="With map location only",
		widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
	)


# Allowed video extensions and max size (50MB) for property video upload
PROPERTY_VIDEO_ALLOWED_EXTENSIONS = (".mp4", ".mov", ".avi")
PROPERTY_VIDEO_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "title",
            "property_type",
            "location",
            "neighborhood",
            "nearby_shopping_center",
            "monthly_rent",
            "description",
            "is_available",
            "latitude",
            "longitude",
            "video",
        ]
        widgets = {
        	"title": forms.TextInput(attrs={"class": "form-control"}),
        	"property_type": forms.Select(attrs={"class": "form-select"}),
        	"location": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Machakos CBD, near Police Station"}),
        	"neighborhood": forms.Select(attrs={"class": "form-select"}),
        	"nearby_shopping_center": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Machakos Shopping Centre"}),
        	"monthly_rent": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Monthly rent in KES"}),
        	"description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        	"is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        	"latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001", "placeholder": "Optional"}),
        	"longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001", "placeholder": "Optional"}),
        	"video": forms.FileInput(attrs={"class": "form-control", "accept": "video/mp4,video/quicktime,video/x-msvideo"}),
        }

    def clean_video(self):
        """Validate video file type (.mp4, .mov, .avi) and max size (50MB)."""
        video = self.cleaned_data.get("video")
        if not video:
            return video
        ext = "." + video.name.rsplit(".", 1)[-1].lower() if "." in video.name else ""
        if ext not in PROPERTY_VIDEO_ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                "Allowed formats: MP4, MOV, AVI. You uploaded a file with extension '%s'." % (ext or "(none)")
            )
        if video.size > PROPERTY_VIDEO_MAX_SIZE_BYTES:
            raise forms.ValidationError(
                "Video must be 50 MB or smaller. Your file is %.1f MB."
                % (video.size / (1024 * 1024))
            )
        return video


class PropertyImageForm(forms.ModelForm):
    class Meta:
        model = PropertyImage
        fields = ["image", "caption"]


PropertyImageFormSet = inlineformset_factory(
    Property, PropertyImage, form=PropertyImageForm, extra=3, can_delete=True
)


class PropertyInquiryForm(forms.ModelForm):
	class Meta:
		model = PropertyInquiry
		fields = ["message"]
		widget = forms.Textarea
		widgets = {
			"message": forms.Textarea(
				attrs={
					"class": "form-control",
					"rows": 4,
					"placeholder": "Write your message here...",
				}
			)
		}


class MessageForm(forms.Form):
	"""Form for sending threaded messages in inquiry conversations (Phase 1)."""
	body = forms.CharField(
		max_length=2000,
		widget=forms.Textarea(
			attrs={
				"class": "form-control",
				"rows": 4,
				"placeholder": "Type your message...",
			}
		),
		help_text="Maximum 2000 characters.",
	)
	
	def clean_body(self):
		body = self.cleaned_data.get("body", "").strip()
		if not body:
			raise forms.ValidationError("Message cannot be empty.")
		if len(body) > 2000:
			raise forms.ValidationError("Message must be 2000 characters or less.")
		return body


class TenantAllocationForm(forms.ModelForm):
	"""
	Landlord-facing form to allocate a tenant to one of their properties.
	"""

	class Meta:
		model = TenantAllocation
		fields = ["property", "tenant", "room_number", "start_date", "end_date"]
		widgets = {
			"property": forms.Select(attrs={"class": "form-select"}),
			"tenant": forms.Select(attrs={"class": "form-select"}),
			"room_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional"}),
			"start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
			"end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
		}

	def __init__(self, *args, landlord=None, **kwargs):
		super().__init__(*args, **kwargs)
		if landlord is not None:
			qs = Property.objects.filter(landlord=landlord)
			self.fields["property"].queryset = qs
			self.fields["property"].choices = [
				("", "---------"),
				*[(p.pk, f"{p.title} — KES {p.monthly_rent:,.0f}/month") for p in qs],
			]
		# Only show tenant users
		self.fields["tenant"].queryset = User.objects.filter(profile__role="tenant").order_by("username")
