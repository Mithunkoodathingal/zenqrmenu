# restaurant/debug_views.py
import json
import logging
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Protect this endpoint with a secret token passed as GET or POST param ?secret=...
DEBUG_SECRET = getattr(settings, "DEBUG_ENDPOINT_SECRET", None)

def _check_secret(request):
    provided = request.GET.get("secret") or request.POST.get("secret")
    if not DEBUG_SECRET or provided != DEBUG_SECRET:
        return False
    return True

@csrf_exempt
@require_http_methods(["GET", "POST"])
def diagnostic(request):
    """Return key email settings and perform a one-off Brevo API test using production config.

    Use: GET /__debug/diagnostic/?secret=<TOKEN>&test_send=1&to=you@domain.tld
    """
    if not _check_secret(request):
        return HttpResponseForbidden("Forbidden")

    # Basic config info
    info = {
        "DEFAULT_FROM_EMAIL": repr(getattr(settings, "DEFAULT_FROM_EMAIL", None)),
        "SERVER_EMAIL": repr(getattr(settings, "SERVER_EMAIL", None)),
        "EMAIL_BACKEND": getattr(settings, "EMAIL_BACKEND", None),
        "ANYMAIL": getattr(settings, "ANYMAIL", None),
        "BREVO_API_KEY_present": bool(getattr(settings, "ANYMAIL", {}).get("BREVO", {}).get("API_KEY")) or bool(getattr(settings, "BREVO_API_KEY", None)),
    }

    # If ?test_send=1 and &to=..., perform a Brevo API POST with the same key & from address
    if request.GET.get("test_send") in ("1", "true", "True"):
        to_addr = request.GET.get("to") or request.POST.get("to")
        if not to_addr:
            info["test_send_error"] = "missing 'to' parameter"
        else:
            # Build sender email (prefer DEFAULT_FROM_EMAIL, but use plain address)
            from_header = getattr(settings, "DEFAULT_FROM_EMAIL", "hello@zenqrmenu.com")
            if "<" in from_header and ">" in from_header:
                name = from_header.split("<", 1)[0].strip()
                from_addr = from_header.split("<", 1)[1].split(">", 1)[0].strip()
            else:
                from_addr = from_header
                name = "Zen QR Menu"

            # get API key from ANYMAIL or top-level var
            api_key = None
            anymail = getattr(settings, "ANYMAIL", {}) or {}
            brevo_info = anymail.get("BREVO") or anymail.get("SENDINBLUE") or {}
            api_key = brevo_info.get("API_KEY") or getattr(settings, "BREVO_API_KEY", None) or getattr(settings, "ANYMAIL_BREVO_API_KEY", None)

            if not api_key:
                info["test_send_error"] = "No BREVO API key found in settings"
            else:
                payload = {
                    "sender": {"name": name, "email": from_addr},
                    "to": [{"email": to_addr}],
                    "subject": "Diagnostic test from zenqrmenu",
                    "textContent": "This is a diagnostic test. If you get this, Brevo accepted the sender."
                }
                headers = {"api-key": api_key, "Content-Type": "application/json"}
                try:
                    r = requests.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=15)
                    info["test_send_status"] = r.status_code
                    # keep limited response body for safety
                    info["test_send_body"] = r.text[:800]
                    logger.info("Diagnostic test sent: status=%s body=%s", r.status_code, r.text[:500])
                except Exception as exc:
                    info["test_send_exception"] = str(exc)

    return JsonResponse(info)
