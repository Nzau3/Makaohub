from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile
import re


class RoleBasedUserCreationForm(UserCreationForm):
    """Extended UserCreationForm with role selection."""
    
    role = forms.ChoiceField(
        choices=[('tenant', 'Tenant'), ('landlord', 'Landlord')],
        widget=forms.RadioSelect,
        label="I am a"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.profile.role = self.cleaned_data['role']
            user.profile.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        label="Mobile Number",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 0712345678',
            'data-bs-toggle': 'tooltip',
            'data-bs-placement': 'top',
            'title': 'Enter mobile number to unlock payment-based features.'
        })
    )

    class Meta:
        model = Profile
        fields = ['phone_number']

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        # Kenyan phone: starts with 07 or 01, 10 digits
        if not re.match(r'^(07|01)\d{8}$', phone):
            raise forms.ValidationError('Enter a valid Kenyan mobile number (e.g. 0712345678 or 0112345678).')
        return phone
