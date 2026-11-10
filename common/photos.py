from rest_framework.exceptions import ValidationError

PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


def take_photo(request, obj, attr="profile_photo", field="profile_photo"):
    """Apply an uploaded photo from `field`. Sending the field empty removes the photo; leaving it out keeps it."""
    if field not in request.data and field not in request.FILES:
        return
    f = request.FILES.get(field)
    current = getattr(obj, attr)
    if f is None:
        if current:
            current.delete(save=False)
        setattr(obj, attr, None)
        return
    if f.content_type not in PHOTO_TYPES or f.size > 5 * 1024 * 1024:
        raise ValidationError({field: ["Use a JPG, PNG or WebP photo under 5 MB."]})
    setattr(obj, attr, f)
