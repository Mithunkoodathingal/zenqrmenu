def note_out(n):
    return {"id": n.id, "order": n.order_id, "note": n.note, "note_type": n.note_type, "is_internal": n.is_internal,
            "is_pinned": n.is_pinned, "created_at": n.created_at, "created_by": n.created_by}


def order_fields(order):
    ticket = getattr(order, "kitchen_ticket", None) if hasattr(order, "kitchen_ticket") else None
    notes = [note_out(n) for n in order.kitchen_notes.filter(archived_at__isnull=True)]
    return {"kitchen_priority": ticket.priority if ticket else "normal", "kitchen_notes": notes}
