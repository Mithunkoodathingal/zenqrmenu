from django import forms
from .models import FoodItem, Restaurant
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from allauth.account.models import EmailAddress




class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ['name', 'address', 'about', 'cover_image', 'logo']   # include logo

class SignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'form-control'}),
        help_text="A valid email is required (we'll send a confirmation email)."
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        """
        Validate email format. If email already exists:
        - If it is associated with an EmailAddress that is verified -> reject (duplicate).
        - If it's associated but unverified -> allow the form (signup view will resend confirmation).
        """
        email = (self.cleaned_data.get("email") or "").strip()
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError("Enter a valid email address.")

        # If any verified EmailAddress exists for this email, block signup (duplicate)
        if EmailAddress.objects.filter(email__iexact=email, verified=True).exists():
            raise ValidationError("A user with that email already exists.")

        # If a User exists and has an EmailAddress that is unverified, we allow signup to proceed
        # The view will catch this and resend the confirmation instead of creating a duplicate user.
        return email
            return email

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise ValidationError("This field is required.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def _derive_username_from_email(self, email):
        base = "user"
        if email:
            base = email.split("@", 1)[0]
            base = "".join(ch for ch in base if ch.isalnum() or ch in ("_", "."))
            if base == "":
                base = "user"
        candidate = base
        suffix = 0
        while User.objects.filter(username=candidate).exists():
            suffix += 1
            candidate = f"{base}{suffix}"
        return candidate

    def save(self, request=None):
        """
        Create user, ensure EmailAddress exists and send confirmation email (if request provided).
        Return (user, redirect_url_or_none) for allauth compatibility.
        """
        user = super().save(commit=False)
        email = (self.cleaned_data.get("email") or "").strip()
        user.email = email

        # Keep user inactive until confirmation (production-safe)
        try:
            user.is_active = False
        except Exception:
            pass

        user.save()

        # Ensure EmailAddress exists and send confirmation if request provided
        ea, created = EmailAddress.objects.get_or_create(
            user=user,
            email=email,
            defaults={'verified': False, 'primary': True}
        )

        # send confirmation using the request (console backend will print it)
        if request is not None:
            try:
                ea.send_confirmation(request)
            except Exception:
                import logging
                logging.exception("Failed to send confirmation for %s", email)

        # compatibility attribute for allauth (passkey flows)
        self.by_passkey = False

        return user, None

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

