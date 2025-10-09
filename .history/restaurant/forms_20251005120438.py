from django import forms
from .models import FoodItem, Restaurant
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
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
        email = (self.cleaned_data.get("email") or "").strip()
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError("Enter a valid email address.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")
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
        Create and return (user, redirect_url_or_none) so allauth's SignupView can unpack it.
        Setting self.by_passkey = False for compatibility with passkey checks.
        """
        # create instance without committing fully
        user = super().save(commit=False)
        email = (self.cleaned_data.get("email") or "").strip()
        user.email = email

        # If username blank for some reason, derive from email
        if not getattr(user, "username", None):
            user.username = self._derive_username_from_email(email)

        # Keep user inactive until email confirmation (change if you want immediate activation)
        try:
            user.is_active = False
        except Exception:
            pass

        user.save()

        # Ensure EmailAddress exists for allauth flows
        if email:
            EmailAddress.objects.get_or_create(
                user=user,
                email=email,
                defaults={'verified': False, 'primary': True}
            )

        # Compatibility attributes allauth expects
        # (passkey flow detection etc.) — default to False
        self.by_passkey = False

        # Return tuple as allauth expects
        return user, None

    # allauth may call try_save; provide it too
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

