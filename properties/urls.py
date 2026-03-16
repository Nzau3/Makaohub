from django.urls import path
from . import views

app_name = "properties"

urlpatterns = [
    path("", views.property_list, name="list"),
    path("activate-featured/<int:property_id>/", views.activate_featured, name="activate_featured"),
    path("<int:id>/start-featured-payment/", views.start_featured_payment, name="start_featured_payment"),
    path("<int:id>/confirm-featured-payment/", views.confirm_featured_payment, name="confirm_featured_payment"),
    path("allocate/", views.allocate_tenant, name="allocate_tenant"),
    path("map/", views.properties_map_view, name="map"),
    path("<int:id>/", views.property_detail, name="detail"),
    path("<int:id>/edit/", views.property_update, name="update"),
    path("<int:id>/delete/", views.property_delete, name="delete"),
    path("create/", views.property_create, name="create"),
    path("my-properties/", views.my_properties, name="my_properties"),
    path("saved/", views.saved_properties, name="saved"),
    path("<int:id>/save/", views.save_property, name="save"),
    path("<int:id>/unsave/", views.unsave_property, name="unsave"),
    path("inquire/<int:property_id>/", views.send_inquiry, name="send_inquiry"),
    path("inquiry/<int:inquiry_id>/conversation/", views.inquiry_conversation, name="inquiry_conversation"),
    path("landlord/inquiries/", views.landlord_inquiries, name="landlord_inquiries"),
    path("landlord/inbox/", views.landlord_inbox, name="landlord_inbox"),
    path("tenant/inbox/", views.tenant_inbox, name="tenant_inbox"),
    path("inquiries/", views.property_inquiries, name="inquiries"),
    path("inquiries/<int:id>/", views.inquiry_detail, name="inquiry_detail"),
]
