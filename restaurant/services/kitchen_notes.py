
from django.utils import timezone
from restaurant.models import KitchenNote
from restaurant.services.common import (
    get_order,
    get_kitchen_note,
)

# ==========================================================
# Create Kitchen Note
# ==========================================================

def create_note(
    *,
    restaurant,
    order_id,
    staff,
    note,
    note_type="general",
    is_internal=True,
    is_pinned=False,
):
    """
    Create a kitchen note.
    """

    order = get_order(
        restaurant=restaurant,
        order_id=order_id,
    )

    return KitchenNote.objects.create(
        order=order,
        staff=staff,
        note=note,
        note_type=note_type,
        is_internal=is_internal,
        is_pinned=is_pinned,
    )

# ==========================================================
# Update Kitchen Note
# ==========================================================

def update_note(
    *,
    restaurant,
    note_id,
    staff,
    edited_reason="",
    **validated_data,
):
    """
    Update an existing kitchen note.
    """

    note = get_kitchen_note(
        restaurant=restaurant,
        note_id=note_id,
    )

    for field, value in validated_data.items():
        setattr(
            note,
            field,
            value,
        )

    note.edited_by = staff
    note.edited_reason = edited_reason
    note.edited_at = timezone.now()

    update_fields = list(validated_data.keys())

    update_fields.extend([
        "edited_by",
        "edited_reason",
        "edited_at",
    ])

    note.save(
        update_fields=update_fields,
    )

    return note

# ==========================================================
# Archive Kitchen Note
# ==========================================================

def archive_note(
    *,
    restaurant,
    note_id,
    staff,
    edited_reason="Archived",
):
    """
    Soft delete a kitchen note.
    """

    note = get_kitchen_note(
        restaurant=restaurant,
        note_id=note_id,
    )

    note.is_deleted = True
    note.edited_by = staff
    note.edited_reason = edited_reason
    note.edited_at = timezone.now()

    note.save(
        update_fields=[
            "is_deleted",
            "edited_by",
            "edited_at",
            "edited_reason",
        ]
    )

    return note

# ==========================================================
# List Kitchen Notes
# ==========================================================

def list_notes(
    *,
    restaurant,
    order_id=None,
    note_type=None,
    is_internal=None,
    is_pinned=None,
):
    """
    Return kitchen notes.
    """

    queryset = KitchenNote.objects.filter(
        order__restaurant=restaurant,
        is_deleted=False,
    )

    if order_id:
        queryset = queryset.filter(
            order_id=order_id,
        )

    if note_type:
        queryset = queryset.filter(
            note_type=note_type,
        )

    if is_internal is not None:
        queryset = queryset.filter(
            is_internal=is_internal,
        )

    if is_pinned is not None:
        queryset = queryset.filter(
            is_pinned=is_pinned,
        )

    return queryset.select_related(
        "staff",
        "edited_by",
        "order",
    ).order_by(
        "-is_pinned",
        "-created_at",
    )
    
    
    
