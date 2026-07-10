# -----restaurant/views/delivery_partners.py

# =============================================================================
# restaurant/views/delivery_partners.py
#
# Delivery Partner APIs
#
# Part 1
#
# • DeliveryPartnerListAPIView
# =============================================================================

from django.shortcuts import get_object_or_404

from django.db import transaction

from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from rest_framework import status

from restaurant.models import (
    
    DeliveryPartner,
    
)

from restaurant.serializers import (
    
    DeliveryPartnerSerializer,
    
    DeliveryPartnerListSerializer,
    
)
from restaurant.services.common import get_restaurant

# =============================================================================
# Delivery Partner List API
# =============================================================================

class DeliveryPartnerListAPIView(APIView):
    """
    Retrieve all delivery partners
    belonging to the authenticated restaurant.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    # -------------------------------------------------------------------------
    # GET
    # -------------------------------------------------------------------------

    def get(self, request):

        # ---------------------------------------------------------------------
        # Restaurant
        # ---------------------------------------------------------------------

        restaurant = get_restaurant(request)

        if restaurant is None:

            return Response(
                {
                    "success": False,
                    "message": "Restaurant not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---------------------------------------------------------------------
        # Queryset
        # ---------------------------------------------------------------------

        queryset = (
            DeliveryPartner.objects
            .filter(
                restaurant=restaurant,
            )
            .order_by(
                "first_name",
                "last_name",
            )
        )

        # ---------------------------------------------------------------------
        # Serialization
        # ---------------------------------------------------------------------

        serializer = DeliveryPartnerListSerializer(
            queryset,
            many=True,
            context={
                "request": request,
            },
        )

        # ---------------------------------------------------------------------
        # Response
        # ---------------------------------------------------------------------

        return Response(
            {
                "success": True,
                "count": queryset.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
        
# =============================================================================
# Delivery Partner Create API
# =============================================================================

class DeliveryPartnerCreateAPIView(APIView):
    """
    Create a new delivery partner for the
    authenticated restaurant.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @transaction.atomic
    def post(self, request):

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
        # Serializer
        # ==========================================================

        serializer = DeliveryPartnerSerializer(

            data=request.data,

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
        # Duplicate Phone Check
        # ==========================================================

        phone = serializer.validated_data.get(
            "phone"
        )

        if DeliveryPartner.objects.filter(
            phone=phone
        ).exists():

            return Response(
                {
                    "success": False,
                    "message": (
                        "A delivery partner with "
                        "this phone number already exists."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Save
        # ==========================================================

        partner = serializer.save(

            restaurant=restaurant

        )

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Delivery partner created "
                    "successfully."
                ),
                "delivery_partner": (
                    DeliveryPartnerSerializer(
                        partner,
                        context={
                            "request": request,
                        },
                    ).data
                ),
            },
            status=status.HTTP_201_CREATED,
        )
        
        
# =============================================================================
# Delivery Partner Detail API
# =============================================================================

class DeliveryPartnerDetailAPIView(APIView):
    """
    Retrieve a single delivery partner.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
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
        # Partner
        # ==========================================================

        partner = get_object_or_404(

            DeliveryPartner,

            id=partner_id,

            restaurant=restaurant,

        )

        # ==========================================================
        # Serialize
        # ==========================================================

        serializer = DeliveryPartnerSerializer(

            partner,

            context={
                "request": request,
            },

        )

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,
                "delivery_partner": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
        
        
# =============================================================================
# Delivery Partner Update API
# =============================================================================

class DeliveryPartnerUpdateAPIView(APIView):
    """
    Update an existing delivery partner.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @transaction.atomic
    def patch(
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

        serializer = DeliveryPartnerSerializer(

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
        # Phone Number Validation
        # ==========================================================

        phone = serializer.validated_data.get(
            "phone"
        )

        if phone:

            exists = DeliveryPartner.objects.filter(

                phone=phone,

            ).exclude(

                id=partner.id,

            ).exists()

            if exists:

                return Response(
                    {
                        "success": False,
                        "message": (
                            "Another delivery partner "
                            "already uses this phone number."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ==========================================================
        # Save
        # ==========================================================

        partner = serializer.save()

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Delivery partner updated successfully."
                ),
                "delivery_partner": DeliveryPartnerSerializer(
                    partner,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_200_OK,
        )
        
        
# =============================================================================
# Delivery Partner Delete API
# =============================================================================

class DeliveryPartnerDeleteAPIView(APIView):
    """
    Delete a delivery partner.

    Prevent deletion if the partner is assigned
    to any active order.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @transaction.atomic
    def delete(
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
        # Active Assignment Check
        # ==========================================================

        active_orders = partner.orders.filter(

            delivery_status__in=[
                "assigned",
                "picked",
                "out_for_delivery",
            ],

            is_deleted=False,

        ).exists()

        if active_orders:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Cannot delete a delivery partner "
                        "who has active deliveries."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Delete
        # ==========================================================

        partner.delete()

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Delivery partner deleted successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )
        
        
