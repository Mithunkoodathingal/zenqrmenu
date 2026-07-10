# -----restaurant/views/delivery_availability.py

# =============================================================================
# restaurant/views/delivery_availability.py
#
# Delivery Availability APIs
# =============================================================================

from django.db import transaction

from django.shortcuts import get_object_or_404

from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from rest_framework import status

from restaurant.models import (
    
    DeliveryPartner,
    
)

from restaurant.serializers import (
    
    DeliveryAvailabilitySerializer,
    
)

from restaurant.services.delivery_partner import update_partner_availability

from restaurant.services.common import (
    
    get_restaurant,
    
)


# =============================================================================
# Delivery Availability API
# =============================================================================

class DeliveryAvailabilityAPIView(APIView):
    """
    Update the availability status of a
    delivery partner.

    Endpoint
    --------
    POST /delivery-partners/<partner_id>/availability/

    Request
    -------
    {
        "is_available": true
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
        # Serializer
        # ==========================================================

        serializer = DeliveryAvailabilitySerializer(

            partner,

            data=request.data,

            partial=True,

            context={
                "request": request,
            },

        )

        if not serializer.is_valid():

            return Response(
                {
                    "success": False,
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Save
        # ==========================================================

        serializer.save()

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Delivery partner availability "
                    "updated successfully."
                ),
                "delivery_partner": {

                    "id": partner.id,

                    "name": partner.full_name,

                    "is_available": partner.is_available,

                    "is_active": partner.is_active,

                },
            },
            status=status.HTTP_200_OK,
        )
        
