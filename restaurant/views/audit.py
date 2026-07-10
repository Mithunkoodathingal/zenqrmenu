from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from restaurant.serializers import (
    
    AuditLogSerializer,
    
    AuditLogFilterSerializer,
    
)

from restaurant.services import (
    
    get_restaurant,
    
    get_staff_by_user,
    
)

from restaurant.services.audit import (

    get_audit_logs,

)

from restaurant.services.permissions import (
    
    user_can_view_reports,
    
)


# ==========================================================
# Audit Log API
# ==========================================================

class AuditLogAPIView(APIView):
    """
    View audit logs.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):

        # ------------------------------------------------------
        # Restaurant
        # ------------------------------------------------------

        restaurant = get_restaurant(request)

        # ------------------------------------------------------
        # Logged-in Staff
        # ------------------------------------------------------

        staff = get_staff_by_user(
            restaurant=restaurant,
            user=request.user,
        )

        # ------------------------------------------------------
        # Permission
        # ------------------------------------------------------

        if not user_can_view_reports(staff):

            raise PermissionDenied(
                "You do not have permission to view audit logs."
            )

        # ------------------------------------------------------
        # Filters
        # ------------------------------------------------------

        filter_serializer = AuditLogFilterSerializer(
            data=request.query_params,
        )

        filter_serializer.is_valid(
            raise_exception=True,
        )

        # ------------------------------------------------------
        # Audit Logs
        # ------------------------------------------------------

        audit_logs = get_audit_logs(
            restaurant=restaurant,
            **filter_serializer.validated_data,
        )

        serializer = AuditLogSerializer(
            audit_logs,
            many=True,
        )

        return Response(
            serializer.data,
        )
        
        
        
