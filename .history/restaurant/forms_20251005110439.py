from django import forms
from .models import FoodItem, Restaurant
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
# restaurant/forms.py
from allauth.account.forms import SignupForm as AllAuthSignupForm
from django import forms
from django.contrib.auth.models import User

class SignupForm(AllAuthSignupForm):
    # Add any extra fields here if needed (email exists already)
    def save(self, request):
        # call parent to create user and EmailAddress appropriately
        user = super().save(request)
        # ensure user is inactive until verification (allauth might already handle this)
        user.is_active = False
        user.save(update_fields=['is_active'])
        return user



class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ['name', 'address', 'about', 'cover_image', 'logo']   # include logo

class SignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'form-control'}),
        help_text="A valid email is required (we'll send a welcome email)."
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        # validate email format
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError("Enter a valid email address.")

        # check uniqueness (case-insensitive)
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email


class FoodItemForm(forms.ModelForm):
    addon_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'addon-input',
            'placeholder': 'Type add-ons like "Cheese:10" and press Enter'
        }),
        label='Add-Ons'
    )

    class Meta:
        model = FoodItem
        fields = ['category', 'name', 'price', 'description', 'image']

