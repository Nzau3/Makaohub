from django.contrib import admin

from .models import Property, PropertyImage, PropertyInquiry, SavedProperty


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
	list_display = ("title", "landlord", "property_type", "location", "monthly_rent", "is_available", "created_at")
	list_filter = ("is_available", "property_type", "neighborhood")
	search_fields = ("title", "location", "landlord__username")


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
	list_display = ("property", "caption", "uploaded_at")
	search_fields = ("property__title", "caption")


@admin.register(PropertyInquiry)
class PropertyInquiryAdmin(admin.ModelAdmin):
	list_display = ("property", "name", "email", "status", "created_at")
	list_filter = ("status",)
	search_fields = ("property__title", "name", "email")


@admin.register(SavedProperty)
class SavedPropertyAdmin(admin.ModelAdmin):
	list_display = ("tenant", "property", "saved_at")
	search_fields = ("tenant__username", "property__title")
