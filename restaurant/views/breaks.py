from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from restaurant.serializers import (
    BreakFilterSerializer,
    StaffBreakSerializer,
    BreakStartSerializer,
    BreakEndSerializer,
)

from restaurant.services import (
    get_restaurant,
    start_break,
    end_break,
    get_breaks,
)

# ==========================================================
# Staff Break Start API
# ==========================================================

class StaffBreakStartAPIView(APIView):
    """
    Start a staff break.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        restaurant = get_restaurant(request)

        serializer = BreakStartSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        staff_break = start_break(
            restaurant=restaurant,
            staff_id=serializer.validated_data["staff_id"],
        )

        return Response(
            StaffBreakSerializer(
                staff_break,
            ).data,
            status=status.HTTP_201_CREATED,
        )

# ==========================================================
# Staff Break End API
# ==========================================================

class StaffBreakEndAPIView(APIView):
    """
    End a staff break.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        restaurant = get_restaurant(request)

        serializer = BreakEndSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        staff_break = end_break(
            restaurant=restaurant,
            staff_id=serializer.validated_data["staff_id"],
        )

        return Response(
            StaffBreakSerializer(
                staff_break,
            ).data,
            status=status.HTTP_200_OK,
        )

# ==========================================================
# Staff Break List API
# ==========================================================

class StaffBreakAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        restaurant = get_restaurant(request)

        filter_serializer = BreakFilterSerializer(
            data=request.query_params,
        )

        filter_serializer.is_valid(
            raise_exception=True,
        )

        breaks = get_breaks(
            restaurant=restaurant,
            **filter_serializer.validated_data,
        )

        serializer = StaffBreakSerializer(
            breaks,
            many=True,
        )

        return Response(serializer.data)
        
        
        
