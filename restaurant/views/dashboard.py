# -----restaurant/views/dashboard.py

# =============================================================================
# restaurant/views/dashboard.py
#
# Dashboard APIs
#
# Part 1
#
# • Imports
# • DashboardAPIView
# =============================================================================

from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from rest_framework import status

from django.db.models import Sum, Count

from django.utils import timezone

from restaurant.models import Order

from restaurant.services.dashboard import (
    
    get_dashboard_data,
    
)

from restaurant.services.common import (
    
    get_restaurant,
    
)


# =============================================================================
# Dashboard API
# =============================================================================

class DashboardAPIView(APIView):
    """
    Restaurant Dashboard API.

    Returns the complete dashboard payload
    required by the Restaurant Dashboard.

    Endpoint
    --------
    GET /api/dashboard/

    Includes
    --------
    • Dashboard Cards

    • Today's Sales

    • Monthly Sales

    • Pending Orders

    • Active Orders

    • Customers Today

    • Delivery Partners

    • Inventory Alerts

    • Recent Orders

    • Top Selling Items

    • Charts

    • Order Summary
    """

    permission_classes = [
        IsAuthenticated,
    ]

    # =========================================================================
    # GET
    # =========================================================================

    def get(
        self,
        request,
    ):

        # ==========================================================
        # Restaurant
        # ==========================================================

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Restaurant not found."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ==========================================================
        # Dashboard Data
        # ==========================================================

        try:

            dashboard = get_dashboard_data(
                restaurant
            )

        except Exception as exc:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Unable to load dashboard."
                    ),
                    "error": str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,
                "dashboard": dashboard,
            },
            status=status.HTTP_200_OK,
        )
        
