from django.urls import path

# Importing from lovable_schema applies the explicit drf-spectacular
# contracts before the views are registered in urlpatterns.
from restaurant.lovable_schema import (
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

# Apply the final runtime-contract corrections after the base Lovable schema
# annotations have been attached.
import restaurant.lovable_schema_contract_fixes  # noqa: F401,E402

urlpatterns = [
    # Orders
    path("api/orders/<int:order_id>/cancel/", OrderCancelAPIView.as_view(), name="api-order-cancel"),
    path("api/orders/<int:order_id>/print-status/", OrderPrintStatusAPIView.as_view(), name="api-order-print-status"),

    # Restaurant location / fulfillment
    path("api/restaurant/location/", RestaurantLocationAPIView.as_view(), name="api-restaurant-location"),
    path("api/restaurants/<int:restaurant_id>/delivery-summary/", DeliverySummaryAPIView.as_view(), name="api-delivery-summary"),
    path("api/restaurants/<int:restaurant_id>/fulfillment-options/", FulfillmentOptionsAPIView.as_view(), name="api-fulfillment-options"),

    # Delivery partners
    path("api/delivery-partners/", DeliveryPartnerListCreateAPIView.as_view(), name="api-delivery-partners"),
    path("api/delivery-partners/available/", AvailableDeliveryPartnersAPIView.as_view(), name="api-delivery-partners-available"),
    path("api/delivery-partners/<int:partner_id>/", DeliveryPartnerDetailAPIView.as_view(), name="api-delivery-partner-detail"),
    path("api/delivery-partners/<int:partner_id>/availability/", DeliveryPartnerAvailabilityAPIView.as_view(), name="api-delivery-partner-availability"),
    path("api/delivery-partners/<int:partner_id>/location/", DeliveryPartnerLocationAPIView.as_view(), name="api-delivery-partner-location"),
    path("api/orders/<int:order_id>/assign-partner/", AssignDeliveryPartnerAPIView.as_view(), name="api-order-assign-partner"),
    path("api/orders/<int:order_id>/unassign-partner/", UnassignDeliveryPartnerAPIView.as_view(), name="api-order-unassign-partner"),
    path("api/orders/<int:order_id>/delivery-status/", DeliveryStatusAPIView.as_view(), name="api-order-delivery-status"),
    path("api/orders/<int:order_id>/tracking/", DeliveryTrackingPublicAPIView.as_view(), name="api-order-tracking"),

    # Inventory
    path("api/inventory/", InventoryAPIView.as_view(), name="api-inventory"),
    path("api/inventory/<int:inventory_id>/", InventoryDetailAPIView.as_view(), name="api-inventory-detail"),

    # Coupons
    path("api/coupons/", CouponListCreateAPIView.as_view(), name="api-coupons"),
    path("api/coupons/<int:coupon_id>/", CouponDetailAPIView.as_view(), name="api-coupon-detail"),
    path("api/restaurants/<int:restaurant_id>/coupons/validate/", CouponValidateAPIView.as_view(), name="api-coupon-validate"),

    # Reviews
    path("api/restaurants/<int:restaurant_id>/reviews/", ReviewListCreateAPIView.as_view(), name="api-reviews"),
    path("api/reviews/<int:review_id>/", ReviewDetailAPIView.as_view(), name="api-review-detail"),

    # Reports
    path("api/reports/", ReportsAPIView.as_view(), name="api-reports"),
]
