from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from restaurant.serializers import (
    KDSOrderSerializer,
    KDSPrioritySerializer,
    KDSStatusSerializer,
    KDSNoteSerializer,
    KDSStatisticsSerializer,
)

from restaurant.services.kds import (
    get_kds_orders,
    update_kds_status,
    update_kds_priority,
    get_kds_statistics,
)
from restaurant.services.common import (
    get_restaurant,
    get_staff_by_user,
)
from restaurant.services.kitchen_notes import create_note

# ==========================================================
# KDS Orders API
# ==========================================================

class KDSOrdersAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        restaurant = get_restaurant(request)

        orders = get_kds_orders(
            restaurant=restaurant,
            kitchen_status=request.query_params.get("kitchen_status"),
            priority=request.query_params.get("priority"),
            order_type=request.query_params.get("order_type"),
        )

        serializer = KDSOrderSerializer(
            orders,
            many=True,
        )

        return Response(serializer.data)

# ==========================================================
# KDS Status API
# ==========================================================

class KDSStatusAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):

        restaurant = get_restaurant(request)

        serializer = KDSStatusSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        order = update_kds_status(
            restaurant=restaurant,
            order_id=order_id,
            kitchen_status=serializer.validated_data["kitchen_status"],
        )

        return Response(
            KDSOrderSerializer(order).data,
            status=status.HTTP_200_OK,
        )

# ==========================================================
# KDS Priority API
# ==========================================================

class KDSPriorityAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):

        restaurant = get_restaurant(request)

        serializer = KDSPrioritySerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        order = update_kds_priority(
            restaurant=restaurant,
            order_id=order_id,
            kitchen_priority=serializer.validated_data["kitchen_priority"],
        )

        return Response(
            KDSOrderSerializer(order).data,
            status=status.HTTP_200_OK,
        )

# ==========================================================
# KDS Notes API
# ==========================================================

class KDSNotesAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):

        restaurant = get_restaurant(request)

        staff = get_staff_by_user(
            restaurant=restaurant,
            user=request.user,
        )

        serializer = KDSNoteSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)


        kitchen_note = create_note(
            
            restaurant=restaurant,
            
            order_id=order_id,
            
            staff=staff,
            
            note=serializer.validated_data["note"],
            
            note_type=serializer.validated_data["note_type"],
            
            is_internal=serializer.validated_data["is_internal"],
            
            is_pinned=serializer.validated_data["is_pinned"],
                        
        )

        return Response(
            KDSNoteSerializer(kitchen_note).data,
            status=status.HTTP_201_CREATED,
        )

# ==========================================================
# KDS Statistics API
# ==========================================================

class KDSStatisticsAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        restaurant = get_restaurant(request)

        statistics = get_kds_statistics(
            restaurant=restaurant,
        )

        serializer = KDSStatisticsSerializer(
            statistics,
        )

        return Response(serializer.data)
    
    
    
