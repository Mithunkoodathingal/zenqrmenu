import math
from decimal import Decimal


def haversine_km(lat1, lng1, lat2, lng2):
    """Straight-line distance in kilometres between two points."""
    lat1, lng1, lat2, lng2 = (float(v) for v in (lat1, lng1, lat2, lng2))
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def valid_point(lat, lng):
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lng <= 180 and not (lat == 0 and lng == 0)


def money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))
