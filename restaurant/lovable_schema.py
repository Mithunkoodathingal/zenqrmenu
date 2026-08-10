"""
OpenAPI contracts for the Lovable feature endpoints.

This module applies drf-spectacular's extend_schema() to the existing APIView
methods without changing their runtime behaviour.  The endpoint implementations
remain in restaurant.views.lovable_features; this module only documents them.

Most request/response contracts are taken from restaurant.api_serializers.
Small inline serializers are used only where the existing endpoint payload is
materially different from an older serializer definition.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers

from restaurant import api_serializers as s
from restaurant.views.lovable_features import (
    AvailableDeliveryPartnersAPIView,
    AssignDeliveryPartnerAPIView,
    CouponDetailAPIView,
    CouponListCreateAPIView,
    CouponValidateAPIView,
    DeliveryPartnerAvailabilityAPIView,
    DeliveryPartnerDetailAPIView,
    DeliveryPartnerListCreateAPIView,
    DeliveryPartnerLocationAPIView,
    DeliveryStatusAPIView,
    DeliverySummaryAPIView,
    DeliveryTrackingPublicAPIView,
    FulfillmentOptionsAPIView,
    InventoryAPIView,
    InventoryDetailAPIView,
    OrderCancelAPIView,
    OrderPrintStatusAPIView,
    ReportsAPIView,
    RestaurantLocationAPIView,
    ReviewDetailAPIView,
    ReviewListCreateAPIView,
    UnassignDeliveryPartnerAPIView,
)


ERROR = OpenApiResponse(s.APIErrorSerializer, description="Validation or business-rule error.")
NOT_FOUND = OpenApiResponse(s.APIErrorSerializer, description="Resource or restaurant not found.")


def _path(name, description):
    return OpenApiParameter(name, OpenApiTypes.INT, OpenApiParameter.PATH, required=True, description=description)


def _query(name, description):
    return OpenApiParameter(name, OpenApiTypes.NUMBER, OpenApiParameter.QUERY, required=True, description=description)


# Exact payloads for a few endpoints whose runtime dictionaries differ from
# the older generic serializers in api_serializers.py.
ActualDeliveryStatusRequest = inline_serializer(
    name="ActualDeliveryStatusRequest",
    fields={"delivery_status": serializers.CharField(required=True)},
)

ActualTrackingResponse = inline_serializer(
    name="ActualTrackingResponse",
    fields={
        "success": serializers.BooleanField(),
        "tracking": inline_serializer(
            name="ActualTracking",
            fields={
                "order_id": serializers.IntegerField(),
                "order_number": serializers.CharField(),
                "delivery_status": serializers.CharField(allow_null=True),
                "partner": inline_serializer(
                    name="TrackingPartner",
                    fields={
                        "id": serializers.IntegerField(),
                        "name": serializers.CharField(),
                        "phone": serializers.CharField(),
                        "latitude": serializers.FloatField(allow_null=True),
                        "longitude": serializers.FloatField(allow_null=True),
                        "last_location_update": serializers.DateTimeField(allow_null=True),
                    },
                    allow_null=True,
                    required=False,
                ),
                "delivery_latitude": serializers.FloatField(allow_null=True),
                "delivery_longitude": serializers.FloatField(allow_null=True),
                "assigned_at": serializers.DateTimeField(allow_null=True),
                "picked_at": serializers.DateTimeField(allow_null=True),
                "delivered_at": serializers.DateTimeField(allow_null=True),
            },
        ),
    },
)

ActualCouponValidateRequest = inline_serializer(
    name="ActualCouponValidateRequest",
    fields={
        "code": serializers.CharField(required=True, max_length=50),
        "order_amount": serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0),
        "order_type": serializers.ChoiceField(
            choices=["dinein", "pickup", "delivery"], required=False
        ),
    },
)

ActualCouponValidateResponse = inline_serializer(
    name="ActualCouponValidateResponse",
    fields={
        "success": serializers.BooleanField(),
        "coupon": inline_serializer(
            name="ValidatedCoupon",
            fields={"id": serializers.IntegerField(), "code": serializers.CharField()},
            required=False,
        ),
        "discount_amount": serializers.DecimalField(
            max_digits=12, decimal_places=2, required=False
        ),
        "message": serializers.CharField(required=False),
    },
)

ActualReview = inline_serializer(
    name="ActualReview",
    fields={
        "id": serializers.IntegerField(),
        "customer_name": serializers.CharField(),
        "rating": serializers.IntegerField(),
        "comment": serializers.CharField(allow_blank=True),
        "owner_response": serializers.CharField(allow_blank=True),
        "created_at": serializers.DateTimeField(),
    },
)

ActualReviewListResponse = inline_serializer(
    name="ActualReviewListResponse",
    fields={
        "success": serializers.BooleanField(),
        "count": serializers.IntegerField(),
        "average_rating": serializers.FloatField(),
        # inline_serializer() returns a serializer instance, not a class.
        # ListField is therefore the correct way to express many=True here.
        "reviews": serializers.ListField(child=ActualReview),
    },
)

ActualReviewCreateRequest = inline_serializer(
    name="ActualReviewCreateRequest",
    fields={
        "order_id": serializers.IntegerField(required=False, allow_null=True),
        "customer_name": serializers.CharField(required=False, max_length=120),
        "customer_email": serializers.EmailField(required=False, allow_blank=True),
        "rating": serializers.IntegerField(min_value=1, max_value=5),
        "comment": serializers.CharField(required=False, allow_blank=True),
    },
)

ActualReviewResponse = inline_serializer(
    name="ActualReviewResponse",
    fields={"success": serializers.BooleanField(), "review": ActualReview},
)

ActualReportResponse = inline_serializer(
    name="ActualReportResponse",
    fields={
        "success": serializers.BooleanField(),
        "report": inline_serializer(
            name="ActualReport",
            fields={
                "restaurant": serializers.DictField(),
                "sales": serializers.DictField(),
                "period_sales": serializers.DictField(),
                "orders": serializers.DictField(),
                "menu": serializers.DictField(),
                "staff": serializers.DictField(),
                "delivery": serializers.DictField(),
                "customers": serializers.DictField(),
                "top_items": serializers.ListField(child=serializers.DictField()),
            },
        ),
    },
)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
OrderCancelAPIView.post = extend_schema(
    operation_id="Order_Cancel",
    request=s.OrderCancelRequestSerializer,
    responses={200: s.OrderCancelResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("order_id", "Order primary key.")],
    description="Cancel an active order belonging to the authenticated restaurant.",
)(OrderCancelAPIView.post)

OrderPrintStatusAPIView.patch = extend_schema(
    operation_id="Order_PrintStatus_Update",
    request=s.OrderPrintStatusRequestSerializer,
    responses={200: s.OrderPrintStatusResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("order_id", "Order primary key.")],
    description="Update kitchen and/or receipt print flags for an order.",
)(OrderPrintStatusAPIView.patch)

# ---------------------------------------------------------------------------
# Restaurant location / fulfillment
# ---------------------------------------------------------------------------
RestaurantLocationAPIView.get = extend_schema(
    operation_id="Restaurant_Location_Retrieve",
    responses={200: s.RestaurantLocationResponseSerializer, 401: ERROR, 404: NOT_FOUND},
    description="Return the authenticated restaurant's delivery/location data.",
)(RestaurantLocationAPIView.get)

RestaurantLocationAPIView.patch = extend_schema(
    operation_id="Restaurant_Location_Update",
    request=s.RestaurantLocationUpdateSerializer,
    responses={200: s.RestaurantLocationResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    description="Update supported restaurant location fields.",
)(RestaurantLocationAPIView.patch)

DeliverySummaryAPIView.get = extend_schema(
    operation_id="Restaurant_DeliverySummary",
    auth=[],
    responses={200: s.DeliverySummaryResponseSerializer, 400: ERROR, 404: NOT_FOUND},
    parameters=[_path("restaurant_id", "Restaurant primary key."), _query("latitude", "Customer latitude."), _query("longitude", "Customer longitude.")],
    description="Calculate delivery eligibility, distance, charge and pickup options for a customer location.",
)(DeliverySummaryAPIView.get)

FulfillmentOptionsAPIView.get = extend_schema(
    operation_id="Restaurant_FulfillmentOptions",
    auth=[],
    responses={200: s.FulfillmentOptionsResponseSerializer, 404: NOT_FOUND},
    parameters=[_path("restaurant_id", "Restaurant primary key.")],
    description="Return dine-in, pickup and delivery capabilities for a restaurant.",
)(FulfillmentOptionsAPIView.get)

# ---------------------------------------------------------------------------
# Delivery partners
# ---------------------------------------------------------------------------
DeliveryPartnerListCreateAPIView.get = extend_schema(
    operation_id="DeliveryPartner_List",
    responses={200: s.DeliveryPartnerListResponseSerializer, 401: ERROR, 404: NOT_FOUND},
)(DeliveryPartnerListCreateAPIView.get)

DeliveryPartnerListCreateAPIView.post = extend_schema(
    operation_id="DeliveryPartner_Create",
    request=s.DeliveryPartnerCreateRequestSerializer,
    responses={201: s.DeliveryPartnerResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
)(DeliveryPartnerListCreateAPIView.post)

DeliveryPartnerDetailAPIView.get = extend_schema(
    operation_id="DeliveryPartner_Retrieve",
    responses={200: s.DeliveryPartnerResponseSerializer, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("partner_id", "Delivery partner primary key.")],
)(DeliveryPartnerDetailAPIView.get)

DeliveryPartnerDetailAPIView.patch = extend_schema(
    operation_id="DeliveryPartner_Update",
    request=s.DeliveryPartnerUpdateRequestSerializer,
    responses={200: s.DeliveryPartnerResponseSerializer, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("partner_id", "Delivery partner primary key.")],
)(DeliveryPartnerDetailAPIView.patch)

DeliveryPartnerDetailAPIView.delete = extend_schema(
    operation_id="DeliveryPartner_Deactivate",
    responses={200: s.DeliveryPartnerDeleteResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("partner_id", "Delivery partner primary key.")],
    description="Deactivate a delivery partner. Deletion is intentionally soft/deactivation based.",
)(DeliveryPartnerDetailAPIView.delete)

DeliveryPartnerAvailabilityAPIView.post = extend_schema(
    operation_id="DeliveryPartner_Availability_Update",
    request=s.DeliveryPartnerAvailabilityRequestSerializer,
    responses={200: s.DeliveryPartnerAvailabilityResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("partner_id", "Delivery partner primary key.")],
)(DeliveryPartnerAvailabilityAPIView.post)

DeliveryPartnerLocationAPIView.post = extend_schema(
    operation_id="DeliveryPartner_Location_Update",
    request=s.DeliveryPartnerLocationRequestSerializer,
    responses={200: s.DeliveryPartnerLocationResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("partner_id", "Delivery partner primary key.")],
)(DeliveryPartnerLocationAPIView.post)

AvailableDeliveryPartnersAPIView.get = extend_schema(
    operation_id="DeliveryPartner_AvailableList",
    responses={200: s.DeliveryPartnerListResponseSerializer, 401: ERROR, 404: NOT_FOUND},
)(AvailableDeliveryPartnersAPIView.get)

AssignDeliveryPartnerAPIView.post = extend_schema(
    operation_id="Order_DeliveryPartner_Assign",
    request=s.AssignDeliveryPartnerRequestSerializer,
    responses={200: s.AssignDeliveryPartnerResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("order_id", "Delivery order primary key.")],
)(AssignDeliveryPartnerAPIView.post)

UnassignDeliveryPartnerAPIView.post = extend_schema(
    operation_id="Order_DeliveryPartner_Unassign",
    responses={200: s.UnassignDeliveryPartnerResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("order_id", "Delivery order primary key.")],
)(UnassignDeliveryPartnerAPIView.post)

DeliveryStatusAPIView.patch = extend_schema(
    operation_id="Order_DeliveryStatus_Update",
    request=ActualDeliveryStatusRequest,
    responses={200: s.DeliveryStatusResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("order_id", "Delivery order primary key.")],
)(DeliveryStatusAPIView.patch)

DeliveryTrackingPublicAPIView.get = extend_schema(
    operation_id="Order_DeliveryTracking_Retrieve",
    auth=[],
    responses={200: ActualTrackingResponse, 400: ERROR, 404: NOT_FOUND},
    parameters=[_path("order_id", "Delivery order primary key.")],
)(DeliveryTrackingPublicAPIView.get)

# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
InventoryAPIView.get = extend_schema(
    operation_id="Inventory_List",
    responses={200: s.InventoryListResponseSerializer, 401: ERROR, 404: NOT_FOUND},
)(InventoryAPIView.get)

InventoryAPIView.post = extend_schema(
    operation_id="Inventory_Create",
    request=s.InventoryCreateRequestSerializer,
    responses={201: s.InventoryCreateResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
)(InventoryAPIView.post)

InventoryDetailAPIView.patch = extend_schema(
    operation_id="Inventory_Update",
    request=s.InventoryUpdateRequestSerializer,
    responses={200: s.InventoryUpdateResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("inventory_id", "Inventory item primary key.")],
)(InventoryDetailAPIView.patch)

InventoryDetailAPIView.delete = extend_schema(
    operation_id="Inventory_Archive",
    responses={200: s.InventoryDeleteResponseSerializer, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("inventory_id", "Inventory item primary key.")],
    description="Archive an inventory item by setting is_active=false.",
)(InventoryDetailAPIView.delete)

# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
CouponListCreateAPIView.get = extend_schema(
    operation_id="Coupon_List",
    responses={200: s.CouponListResponseSerializer, 401: ERROR, 404: NOT_FOUND},
)(CouponListCreateAPIView.get)

CouponListCreateAPIView.post = extend_schema(
    operation_id="Coupon_Create",
    request=s.CouponCreateRequestSerializer,
    responses={201: s.CouponResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
)(CouponListCreateAPIView.post)

CouponDetailAPIView.patch = extend_schema(
    operation_id="Coupon_Update",
    request=s.CouponUpdateRequestSerializer,
    responses={200: s.CouponResponseSerializer, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("coupon_id", "Coupon primary key.")],
)(CouponDetailAPIView.patch)

CouponDetailAPIView.delete = extend_schema(
    operation_id="Coupon_Deactivate",
    responses={200: s.CouponDeleteResponseSerializer, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("coupon_id", "Coupon primary key.")],
    description="Deactivate a coupon rather than physically deleting it.",
)(CouponDetailAPIView.delete)

CouponValidateAPIView.post = extend_schema(
    operation_id="Coupon_Validate",
    auth=[],
    request=ActualCouponValidateRequest,
    responses={200: ActualCouponValidateResponse, 400: ERROR, 404: NOT_FOUND},
    parameters=[_path("restaurant_id", "Restaurant primary key.")],
)(CouponValidateAPIView.post)

# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------
ReviewListCreateAPIView.get = extend_schema(
    operation_id="Review_List",
    auth=[],
    responses={200: ActualReviewListResponse, 404: NOT_FOUND},
    parameters=[_path("restaurant_id", "Restaurant primary key.")],
)(ReviewListCreateAPIView.get)

ReviewListCreateAPIView.post = extend_schema(
    operation_id="Review_Create",
    auth=[],
    request=ActualReviewCreateRequest,
    responses={201: ActualReviewResponse, 400: ERROR, 404: NOT_FOUND},
    parameters=[_path("restaurant_id", "Restaurant primary key.")],
)(ReviewListCreateAPIView.post)

ReviewDetailAPIView.patch = extend_schema(
    operation_id="Review_Update",
    request=s.ReviewUpdateRequestSerializer,
    responses={200: ActualReviewResponse, 400: ERROR, 401: ERROR, 404: NOT_FOUND},
    parameters=[_path("review_id", "Review primary key.")],
)(ReviewDetailAPIView.patch)

# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
ReportsAPIView.get = extend_schema(
    operation_id="Reports_Retrieve",
    responses={200: ActualReportResponse, 401: ERROR, 404: NOT_FOUND},
    description="Return restaurant sales, order, menu, staff, delivery, customer and top-item statistics.",
)(ReportsAPIView.get)


# Re-export the decorated classes so urls_extra.py can import one stable set.
__all__ = [name for name in globals() if name.endswith("APIView")]
