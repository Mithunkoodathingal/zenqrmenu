from django import forms
from .models import FoodItem, Restaurant
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from allauth.account.models import EmailAddress
# restaurant/forms.py (SignupForm)
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from allauth.account.models import EmailAddress

User = get_user_model()

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class':'form-control'}))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError("Enter a valid email address.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def save(self, request=None):
        """
        Create user, EmailAddress and send confirmation email (if request provided).
        Return (user, redirect_url_or_none) — allauth expects a tuple.
        """
        # create user instance
        user = super().save(commit=False)
        user.email = (self.cleaned_data.get('email') or '').strip()
        # default to inactive until verification
        user.is_active = False
        user.save()

        # ensure EmailAddress exists
        ea, created = EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={'verified': False, 'primary': True}
        )

        # send confirmation if we have request (console backend prints it)
        try:
            if request is not None:
                ea.send_confirmation(request)
        except Exception:
            # don't fail signup if email sending fails — log in server logs
            import logging
            logging.exception("Failed to send confirmation for %s", user.email)

        # compatibility attribute expected by some allauth versions
        self.by_passkey = False

        return user, None

    def try_save(self, request):
        return self.save(request)




class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ['name', 'address', 'about', 'cover_image', 'logo']   # include logo



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

