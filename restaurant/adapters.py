# restaurant/adapters.py
from allauth.account.adapter import DefaultAccountAdapter

class NoPrefixAccountAdapter(DefaultAccountAdapter):
    def format_email_subject(self, subject):
        # Return the rendered subject unchanged (no site prefix)
        return subject
