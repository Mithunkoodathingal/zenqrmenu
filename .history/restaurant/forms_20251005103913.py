# restaurant/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from allauth.account.forms import SignupForm as AllAuthSignupForm
from allauth.account.utils import user_email, user_field, user_username
from allauth.account.models import EmailAddress

from .models import FoodItem, Restaurant

User = get_user_model()

# restaurant/forms.py
from django import forms
from django.contrib.auth import get_user_model
from allauth.account.forms import SignupForm as AllAuthSignupForm

User = get_user_model()



class SignupForm(AllAuthSignupForm):
    """
    allauth-compatible signup form.
    We subclass allauth's SignupForm, add server-side email validation/uniqueness check,
    and provide try_save(request) so allauth's SignupView can call it.
    """
    # allauth SignupForm already has email/password fields; we re-use them.
    # Add custom widget attrs for consistent CSS with your templates:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # set bootstrap classes/placeholders if you like
        if 'username' in self.fields:
            self.fields['username'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'User Name',
                'autocomplete': 'username',
            })
        if 'email' in self.fields:
            self.fields['email'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Email',
                'autocomplete': 'email',
            })
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Password',
                'autocomplete': 'new-password',
            })
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Re-write Password',
                'autocomplete': 'new-password',
            })

    def clean_email(self):
        """Validate format and uniqueness (case-insensitive)."""
        email = self.cleaned_data.get("email", "").strip()
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError("Enter a valid email address.")

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    # allauth's SignupView may call try_save(request) if present.
    def try_save(self, request):
        """
        Create and return a user instance. Keep user inactive until email confirmed.
        This method is used by allauth.account.views.SignupView.
        """
        # Use parent save() to create the user and handle password hashing, etc.
        user = super().save(request)
        # Ensure email stored and user inactive until verified (safety)
        if self.cleaned_data.get("email"):
            user.email = self.cleaned_data.get("email").strip()
        # Make user inactive until they confirm email (if you require that)
        user.is_active = False
        user.save(update_fields=['email', 'is_active'])

        # Ensure EmailAddress exists for allauth email confirmation flows
        EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={'verified': False, 'primary': True}
        )
        return user


class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ['name', 'address', 'about', 'cover_image', 'logo']


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
