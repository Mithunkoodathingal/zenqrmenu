"""Small schema corrections for core endpoints whose runtime decorators are incomplete."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from restaurant.serializers import (
    ErrorSerializer,
    RestaurantDeleteResponseSerializer,
    RestaurantNotFoundSerializer,
)
from restaurant.views.views import DeleteRestaurantAPIView


# The runtime view already has a response contract, but its decorator omitted
# operation_id and the restaurant_id path parameter.
DeleteRestaurantAPIView.delete = extend_schema(
    tags=["Restaurant"],
    operation_id="Restaurant_Delete",
    summary="Delete Restaurant",
    description="Soft delete the authenticated user's restaurant.",
    responses={
        200: RestaurantDeleteResponseSerializer,
        403: ErrorSerializer,
        404: RestaurantNotFoundSerializer,
    },
    parameters=[
        OpenApiParameter(
            name="restaurant_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            required=True,
            description="Restaurant primary key.",
        ),
    ],
)(DeleteRestaurantAPIView.delete)
