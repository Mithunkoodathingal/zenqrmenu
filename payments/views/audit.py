from payments.models import PaymentAuditLog


def create_audit_log(
    restaurant,
    action,
    description,
    payment=None,
    request=None,
):

    PaymentAuditLog.objects.create(

        restaurant=restaurant,

        payment=payment,

        action=action,

        description=description,

        ip_address=(
            request.META.get("REMOTE_ADDR")
            if request else None
        ),
    )