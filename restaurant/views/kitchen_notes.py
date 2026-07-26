from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from restaurant.serializers import (
    KDSNoteSerializer,
)

from restaurant.services.common import (
    get_restaurant,
    get_staff_by_user,
)

from restaurant.services.kitchen_notes import (
    create_note,
    update_note,
    archive_note,
    list_notes,
)


# ==========================================================
# Kitchen Notes API
# ==========================================================

class KitchenNotesAPIView(APIView):
    """
    Create and list kitchen notes.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):

        restaurant = get_restaurant(request)

        notes = list_notes(
            restaurant=restaurant,
            order_id=request.query_params.get("order_id"),
            note_type=request.query_params.get("note_type"),
            is_internal=request.query_params.get("is_internal"),
            is_pinned=request.query_params.get("is_pinned"),
        )

        serializer = KDSNoteSerializer(
            notes,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):

        restaurant = get_restaurant(request)

        staff = get_staff_by_user(
            restaurant=restaurant,
            user=request.user,
        )

        serializer = KDSNoteSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        note = create_note(
            restaurant=restaurant,
            order_id=serializer.validated_data["order"],
            staff=staff,
            note=serializer.validated_data["note"],
            note_type=serializer.validated_data["note_type"],
            is_internal=serializer.validated_data["is_internal"],
            is_pinned=serializer.validated_data["is_pinned"],
        )

        return Response(
            KDSNoteSerializer(note).data,
            status=status.HTTP_201_CREATED,
        )
        
        
# ==========================================================
# Kitchen Note Detail API
# ==========================================================

class KitchenNoteAPIView(APIView):
    """
    Retrieve, update and archive a kitchen note.
    """

    permission_classes = [IsAuthenticated]

    def put(self, request, note_id):

        restaurant = get_restaurant(request)

        serializer = KDSNoteSerializer(
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        note = update_note(
            restaurant=restaurant,
            note_id=note_id,
            **serializer.validated_data,
        )

        return Response(
            KDSNoteSerializer(note).data,
        )

    def patch(self, request, note_id):

        restaurant = get_restaurant(request)

        serializer = KDSNoteSerializer(
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        note = update_note(
            restaurant=restaurant,
            note_id=note_id,
            **serializer.validated_data,
        )

        return Response(
            KDSNoteSerializer(note).data,
        )

    def delete(self, request, note_id):

        restaurant = get_restaurant(request)

        archive_note(
            restaurant=restaurant,
            note_id=note_id,
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
        
        
