from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

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
        Create and return (user, redirect_url_or_none), and set attributes
        allauth's SignupView expects on the form (like by_passkey).
        """
        # Create user instance (but don't commit via super().save(commit=False))
        user = super().save(commit=False)
        user.email = (self.cleaned_data.get('email') or "").strip()
        try:
            user.is_active = False
        except Exception:
            pass
        user.save()

        # Ensure EmailAddress exists for allauth confirmation flows
        if user.email:
            EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={'verified': False, 'primary': True}
            )

        # Set attributes that allauth's SignupView may check later
        # (e.g. for passkey/webauthn flows). Default to False for compatibility.
        # This prevents AttributeError in SignupView.form_valid.
        try:
            self.by_passkey = False
        except Exception:
            # ensure attribute exists even if 'self' behaves oddly
            setattr(self, 'by_passkey', False)

        # allauth expects a tuple (user, redirect_url_or_none)
        return user, None

    # ensure try_save exists as some allauth versions call it
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

