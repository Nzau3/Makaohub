from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path('', views.index, name='index'),
    path('start-browsing/', views.start_browsing, name='start_browsing'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]
