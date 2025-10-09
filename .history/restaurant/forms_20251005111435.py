from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from restaurant.models

from allauth.account.models import EmailAddress

User = get_user_model()

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
        email = (self.cleaned_data.get("email") or "").strip()
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError("Enter a valid email address.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def save(self, request=None):
        """
        Create the user and return a tuple (user, redirect_url_or_none)
        so that allauth's SignupView.form_valid can unpack safely.
        If called without request (e.g. from custom view), it still works.
        """
        # Use UserCreationForm.save(commit=False) to create instance
        user = super().save(commit=False)
        user.email = (self.cleaned_data.get('email') or "").strip()
        # Keep inactive until email verification (optional)
        try:
            user.is_active = False
        except Exception:
            pass
        user.save()

        # Ensure EmailAddress for allauth flows
        if user.email:
            EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={'verified': False, 'primary': True}
            )

        # allauth expects a tuple (user, redirect_url_or_none)
        return user, None

    # for safety, implement try_save too (older allauth expects try_save in some flows)
    def try_save(self, request):
        return self.save(request)


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

