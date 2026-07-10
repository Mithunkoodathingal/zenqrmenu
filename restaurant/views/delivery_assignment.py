# -----restaurant/views/delivery_assingnment.py

# =============================================================================
# restaurant/views/delivery_assignment.py
#
# Delivery Assignment APIs
#
# Part 1
#
# • Imports
# • AssignDeliveryPartnerAPIView
# =============================================================================

from django.db import transaction

from django.shortcuts import get_object_or_404

from django.utils import timezone

from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

from rest_framework import status

from restaurant.models import (
    
    Order,
    
    DeliveryPartner,
    
)

from restaurant.serializers import (
    
    DeliveryAssignmentSerializer,
    
)
from restaurant.services.common import get_restaurant


# =============================================================================
# Assign Delivery Partner API
# =============================================================================

class AssignDeliveryPartnerAPIView(APIView):
    """
    Assign a delivery partner to a delivery order.

    Rules

    • Restaurant owner only

    • Order must belong to restaurant

    • Order type must be Delivery

    • Partner must belong to restaurant

    • Partner must be active

    • Partner must be available

    • Prevent duplicate assignment
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @transaction.atomic
    def post(
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
                        "Delivery partner can only "
                        "be assigned to delivery orders."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Already Assigned
        # ==========================================================

        if order.delivery_partner:

            return Response(
                {
                    "success": False,
                    "message": (
                        "A delivery partner is already "
                        "assigned to this order."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Delivery Partner ID
        # ==========================================================

        partner_id = request.data.get(
            "delivery_partner"
        )

        if not partner_id:

            return Response(
                {
                    "success": False,
                    "message": (
                        "delivery_partner is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
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
        # Partner Active
        # ==========================================================

        if not partner.is_active:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Selected delivery partner "
                        "is inactive."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Partner Availability
        # ==========================================================

        if not partner.is_available:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Selected delivery partner "
                        "is currently unavailable."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Assign
        # ==========================================================

        order.delivery_partner = partner

        order.delivery_status = "assigned"

        order.assigned_at = timezone.now()

        order.save(
            update_fields=[
                "delivery_partner",
                "delivery_status",
                "assigned_at",
            ]
        )

        # Optional:
        # partner.is_available = False
        # partner.save(update_fields=["is_available"])

        # ==========================================================
        # Response
        # ==========================================================

        serializer = DeliveryAssignmentSerializer(
            order,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Delivery partner assigned "
                    "successfully."
                ),
                "assignment": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
        
# =============================================================================
# Unassign Delivery Partner API
# =============================================================================

class UnassignDeliveryPartnerAPIView(APIView):
    """
    Remove the assigned delivery partner
    from an order.

    Rules

    • Restaurant owner only

    • Order must belong to restaurant

    • Order must be a delivery order

    • Order must already have an assigned partner

    • Cannot unassign after delivery completion
    """

    permission_classes = [
        IsAuthenticated,
    ]

    @transaction.atomic
    def post(
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
                        "Only delivery orders "
                        "can have delivery partners."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Assignment Exists
        # ==========================================================

        if order.delivery_partner is None:

            return Response(
                {
                    "success": False,
                    "message": (
                        "No delivery partner "
                        "assigned to this order."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Prevent Unassign After Completion
        # ==========================================================

        if order.delivery_status == "delivered":

            return Response(
                {
                    "success": False,
                    "message": (
                        "Delivered orders cannot "
                        "be unassigned."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==========================================================
        # Current Partner
        # ==========================================================

        partner = order.delivery_partner

        # ==========================================================
        # Make Partner Available Again
        # ==========================================================

        partner.is_available = True

        partner.save(
            update_fields=[
                "is_available",
            ]
        )

        # ==========================================================
        # Clear Assignment
        # ==========================================================

        order.delivery_partner = None

        order.delivery_status = "not_required"

        order.assigned_at = None

        order.picked_at = None

        order.delivered_at = None

        order.save(
            update_fields=[
                "delivery_partner",
                "delivery_status",
                "assigned_at",
                "picked_at",
                "delivered_at",
            ]
        )

        # ==========================================================
        # Response
        # ==========================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Delivery partner unassigned "
                    "successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )
        
