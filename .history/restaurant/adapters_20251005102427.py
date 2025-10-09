# restaurant/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class EnsureUsernameEmailAdapter(DefaultAccountAdapter):
    """
    Ensure the User instance has an email and a safe, unique username
    before calling DefaultAccountAdapter.save_user so the user manager
    won't raise ValueError for missing required fields.
    """

    def populate_username(self, request, user):
        # If already set, keep it
        if getattr(user, "username", None):
            return user.username

        # Try to derive from email (request.POST fallback if needed)
        email = getattr(user, "email", None) or (request.POST.get('email') if request and request.POST else None)
        base = "user"
        if email:
            base = email.split("@", 1)[0]
            # sanitize localpart: allow alnum, underscore, dot
            base = "".join(ch for ch in base if ch.isalnum() or ch in ("_", "."))
            if base == "":
                base = "user"

        candidate = base
        suffix = 0
        while User.objects.filter(username=candidate).exists():
            suffix += 1
            candidate = f"{base}{suffix}"
        user.username = candidate
        return user.username

    def save_user(self, request, user, form, commit=True):
        # Ensure email present if available in form.cleaned_data
        try:
            email = form.cleaned_data.get("email") if form and hasattr(form, "cleaned_data") else None
        except Exception:
            email = None

        if not getattr(user, "email", None) and email:
            user.email = email

        # Ensure username is set (populate_username will set it)
        if not getattr(user, "username", None):
            self.populate_username(request, user)

        # Delegate to the default adapter to handle password/save etc.
        return super().save_user(request, user, form, commit=commit)
