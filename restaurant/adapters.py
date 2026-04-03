# restaurant/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

class CustomAccountAdapter(DefaultAccountAdapter):

    def get_password_reset_url(self, request, user, temp_key):
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        return f"https://zenqrmenu.lovable.app/reset-password?uid={uid}&token={temp_key}"