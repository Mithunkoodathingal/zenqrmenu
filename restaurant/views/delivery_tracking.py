# -----restaurant/views/delivery_tracking.py

# =============================================================================
# restaurant/views/delivery_tracking.py
#
# Delivery Tracking APIs
#
# Part 1
#
# • Imports
# • DeliveryTrackingAPIView
# =============================================================================

from django.shortcuts import get_object_or_404

from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from rest_framework import status

from django.db import transaction


from restaurant.models import (
    
    Order,
    
    DeliveryPartner,
    
)

from restaurant.serializers import DeliveryPartnerListSerializer

from restaurant.services.delivery_partner import (
    
    get_delivery_tracking,
    
    update_partner_location,
    
)

from restaurant.services.common import (
    
    get_restaurant,
    
)


# =============================================================================
# Delivery Tracking API
# =============================================================================

class DeliveryTrackingAPIView(APIView):
    """
    Retrieve live delivery tracking information
    for a delivery order.

    Endpoint
    --------
    GET /orders/<order_id>/tracking/

    Returns
    -------
    • Order information
    • Delivery partner
    • Current location
    • Delivery timestamps
    • ETA
    • Delivery distance
    • Delivery charge
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
        order_id,
    ):

        # ==========================================================
        # Restaurant
        # ==========================================================

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ==========================================================
        # Order
        # ==========================================================

        order = get_object_or_404(

            Order,

            id=order_id,

            restaurant=restaurant,

            is_deleted=False,

        )

        # ==========================================================
        # Delivery Orders Only
        # ==========================================================

        if order.order_type != "delivery":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Tracking is available only "
                        "for delivery orders."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Tracking Information
        # ==========================================================

        tracking = get_delivery_tracking(
            order
        )

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,
                "tracking": tracking,
            },
            status=status.HTTP_200_OK,
        )
        
        
# =============================================================================
# Update Partner Location API
# =============================================================================

class UpdatePartnerLocationAPIView(APIView):
    """
    Update the live GPS location of a delivery partner.

    Endpoint
    --------
    POST /delivery-partners/<partner_id>/location/

    Request
    -------
    {
        "latitude": 11.2588,
        "longitude": 75.7804
    }
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @transaction.atomic
    def post(
        self,
        request,
        partner_id,
    ):

        # ==========================================================
        # Restaurant
        # ==========================================================

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ==========================================================
        # Delivery Partner
        # ==========================================================

        partner = get_object_or_404(

            DeliveryPartner,

            id=partner_id,

            restaurant=restaurant,

        )

        # ==========================================================
        # Coordinates
        # ==========================================================

        latitude = request.data.get(
            "latitude"
        )

        longitude = request.data.get(
            "longitude"
        )

        if latitude is None or longitude is None:

            return Response(
                {
                    "success": False,
                    "message": (
                        "latitude and longitude "
                        "are required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Update Location
        # ==========================================================

        try:

            partner = update_partner_location(

                partner,

                latitude,

                longitude,

            )

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Location updated successfully."
                ),
                "partner": {
                    "id": partner.id,
                    "name": partner.full_name,
                    "latitude": (
                        float(partner.current_latitude)
                        if partner.current_latitude is not None
                        else None
                    ),
                    "longitude": (
                        float(partner.current_longitude)
                        if partner.current_longitude is not None
                        else None
                    ),
                    "updated_at": (
                        partner.last_location_update
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )
        
        
# =============================================================================
# Nearby Delivery Partners API
# =============================================================================

class NearbyDeliveryPartnersAPIView(APIView):
    """
    Retrieve all currently available
    delivery partners.

    Endpoint
    --------
    GET /delivery-partners/available/

    Optional Query Parameters
    -------------------------
    is_available=true

    is_active=true

    Future
    ------
    latitude

    longitude

    radius
    """

    permission_classes = [
        IsAuthenticated,
    ]

    # =========================================================================
    # GET
    # =========================================================================

    def get(self, request):

        # ==========================================================
        # Restaurant
        # ==========================================================

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ==========================================================
        # Filters
        # ==========================================================

        queryset = DeliveryPartner.objects.filter(

            restaurant=restaurant,

            is_active=True,

            is_available=True,

        ).order_by(

            "first_name",

            "last_name",

        )

        # ==========================================================
        # Future Filters
        # ==========================================================

        # latitude = request.query_params.get(
        #     "latitude"
        # )
        #
        # longitude = request.query_params.get(
        #     "longitude"
        # )
        #
        # radius = request.query_params.get(
        #     "radius"
        # )
        #
        # Future:
        # Return only nearby delivery partners
        # ordered by distance.

        # ==========================================================
        # Serialization
        # ==========================================================

        serializer = DeliveryPartnerListSerializer(

            queryset,

            many=True,

            context={
                "request": request,
            },

        )

        # ==========================================================
        # Statistics
        # ==========================================================

        available_count = queryset.count()

        busy_count = DeliveryPartner.objects.filter(

            restaurant=restaurant,

            is_active=True,

            is_available=False,

        ).count()

        total_count = DeliveryPartner.objects.filter(

            restaurant=restaurant,

            is_active=True,

        ).count()

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,

                "available_count": available_count,

                "busy_count": busy_count,

                "total_count": total_count,

                "delivery_partners": serializer.data,
            },
            status=status.HTTP_200_OK,
        )