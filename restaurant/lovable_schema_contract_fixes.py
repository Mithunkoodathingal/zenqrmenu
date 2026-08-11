"""Final contract corrections for the Lovable API OpenAPI annotations.

This module contains schema-only corrections for endpoints whose runtime JSON
payloads are assembled manually and therefore do not match the broader
ModelSerializer contracts in restaurant.api_serializers.
"""

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from restaurant import api_serializers as s
from restaurant.views.lovable_features import (
    CouponDetailAPIView,
    CouponListCreateAPIView,
    DeliveryStatusAPIView,
    InventoryAPIView,
    ReviewDetailAPIView,
)


ActualDeliveryStatusResponse = inline_serializer(
    name="ActualDeliveryStatusResponse",
    fields={
        "success": serializers.BooleanField(),
        "order": s.OrderPayloadSerializer(),
    },
)


ActualInventoryItem = inline_serializer(
    name="ActualInventoryItem",
    fields={
        "id": serializers.IntegerField(),
        "name": serializers.CharField(),
        "sku": serializers.CharField(allow_blank=True),
        "unit": serializers.CharField(),
        "quantity": serializers.DecimalField(max_digits=12, decimal_places=3),
        "reorder_level": serializers.DecimalField(max_digits=12, decimal_places=3),
        "cost_price": serializers.DecimalField(max_digits=12, decimal_places=2),
        "food_item": serializers.IntegerField(allow_null=True),
        "low_stock": serializers.BooleanField(),
        "notes": serializers.CharField(allow_blank=True),
    },
)

ActualInventoryListResponse = inline_serializer(
    name="ActualInventoryListResponse",
    fields={
        "success": serializers.BooleanField(),
        "count": serializers.IntegerField(),
        "inventory": serializers.ListField(child=ActualInventoryItem),
    },
)


ActualCoupon = inline_serializer(
    name="ActualCoupon",
    fields={
        "id": serializers.IntegerField(),
        "code": serializers.CharField(),
        "discount_type": serializers.CharField(),
        "value": serializers.DecimalField(max_digits=10, decimal_places=2),
        "minimum_order_amount": serializers.DecimalField(max_digits=10, decimal_places=2),
        "maximum_discount": serializers.DecimalField(
            max_digits=10, decimal_places=2, allow_null=True
        ),
        "usage_limit": serializers.IntegerField(allow_null=True),
        "used_count": serializers.IntegerField(),
        "valid_from": serializers.DateTimeField(allow_null=True),
        "valid_until": serializers.DateTimeField(allow_null=True),
        "applies_to_dinein": serializers.BooleanField(),
        "applies_to_pickup": serializers.BooleanField(),
        "applies_to_delivery": serializers.BooleanField(),
        "is_active": serializers.BooleanField(),
    },
)

ActualCouponListResponse = inline_serializer(
    name="ActualCouponListResponse",
    fields={
        "success": serializers.BooleanField(),
        "count": serializers.IntegerField(),
        "coupons": serializers.ListField(child=ActualCoupon),
    },
)

ActualCouponResponse = inline_serializer(
    name="ActualCouponResponse",
    fields={
        "success": serializers.BooleanField(),
        "coupon": ActualCoupon,
    },
)

ActualCouponDeleteResponse = inline_serializer(
    name="ActualCouponDeleteResponse",
    fields={
        "success": serializers.BooleanField(),
        "message": serializers.CharField(),
    },
)


ActualReviewUpdateRequest = inline_serializer(
    name="ActualReviewUpdateRequest",
    fields={
        "owner_response": serializers.CharField(required=False, allow_blank=True),
        "is_published": serializers.BooleanField(required=False),
    },
)

ActualReviewUpdateResponse = inline_serializer(
    name="ActualReviewUpdateResponse",
    fields={
        "success": serializers.BooleanField(),
        "review": inline_serializer(
            name="ActualReviewUpdatePayload",
            fields={
                "id": serializers.IntegerField(),
                "customer_name": serializers.CharField(),
                "rating": serializers.IntegerField(),
                "comment": serializers.CharField(allow_blank=True),
                "owner_response": serializers.CharField(allow_blank=True),
                "created_at": serializers.DateTimeField(),
            },
        ),
    },
)


# The actual DeliveryStatusAPIView returns success + order and no message.
DeliveryStatusAPIView.patch = extend_schema(
    operation_id="Order_DeliveryStatus_Update",
    request=s.DeliveryStatusRequestSerializer,
    responses={
        200: ActualDeliveryStatusResponse,
        400: s.APIErrorSerializer,
        401: s.APIErrorSerializer,
        404: s.APIErrorSerializer,
    },
)(DeliveryStatusAPIView.patch)


# Inventory GET returns a manually assembled, smaller payload than the
# ModelSerializer used elsewhere in api_serializers.py.
InventoryAPIView.get = extend_schema(
    operation_id="Inventory_List",
    responses={
        200: ActualInventoryListResponse,
        401: s.APIErrorSerializer,
        404: s.APIErrorSerializer,
    },
)(InventoryAPIView.get)


# Coupon endpoints serialize a manually selected subset of Coupon fields.
CouponListCreateAPIView.get = extend_schema(
    operation_id="Coupon_List",
    responses={
        200: ActualCouponListResponse,
        401: s.APIErrorSerializer,
        404: s.APIErrorSerializer,
    },
)(CouponListCreateAPIView.get)

CouponListCreateAPIView.post = extend_schema(
    operation_id="Coupon_Create",
    request=s.CouponCreateRequestSerializer,
    responses={
        201: ActualCouponResponse,
        400: s.APIErrorSerializer,
        401: s.APIErrorSerializer,
        404: s.APIErrorSerializer,
    },
)(CouponListCreateAPIView.post)

CouponDetailAPIView.patch = extend_schema(
    operation_id="Coupon_Update",
    request=s.CouponUpdateRequestSerializer,
    responses={
        200: ActualCouponResponse,
        400: s.APIErrorSerializer,
        401: s.APIErrorSerializer,
        404: s.APIErrorSerializer,
    },
)(CouponDetailAPIView.patch)

CouponDetailAPIView.delete = extend_schema(
    operation_id="Coupon_Deactivate",
    responses={
        200: ActualCouponDeleteResponse,
        401: s.APIErrorSerializer,
        404: s.APIErrorSerializer,
    },
)(CouponDetailAPIView.delete)


# The review PATCH implementation only accepts owner_response/is_published.
ReviewDetailAPIView.patch = extend_schema(
    operation_id="Review_Update",
    request=ActualReviewUpdateRequest,
    responses={
        200: ActualReviewUpdateResponse,
        400: s.APIErrorSerializer,
        401: s.APIErrorSerializer,
        404: s.APIErrorSerializer,
    },
)(ReviewDetailAPIView.patch)
