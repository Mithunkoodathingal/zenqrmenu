from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()

for user in User.objects.all():
    if not user.email:
        continue

    existing = EmailAddress.objects.filter(email=user.email).first()

    if existing:
        if existing.user != user:
            continue

        existing.verified = True
        existing.primary = True
        existing.save()
    else:
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True
        )