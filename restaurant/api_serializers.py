"""
Explicit API serializers for the JSON endpoints used by Lovable and the
supporting API views.

These serializers are intentionally separate from restaurant/serializers.py.
They describe request/response contracts for APIView endpoints whose response
objects are assembled manually in the view/service layer.
"""

from rest_framework import serializers

from restaurant.feature_models import Coupon, InventoryItem, Review



from rest_framework import serializers


# =============================================================================
# PUBLIC MENU BY TABLE
# =============================================================================


class PublicMenuAddonSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    price = serializers.FloatField()


class PublicMenuCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class PublicMenuItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    price = serializers.FloatField()
    image = serializers.CharField(
        allow_null=True,
        required=False,
    )
    category = serializers.IntegerField()
    addons = PublicMenuAddonSerializer(
        many=True,
        required=False,
    )


class PublicMenuRestaurantSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    logo = serializers.CharField(
        allow_null=True,
        required=False,
    )
    cover_image = serializers.CharField(
        allow_null=True,
        required=False,
    )
    address = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
    )


class PublicMenuTableSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    table_number = serializers.IntegerField()


class PublicMenuByTableResponseSerializer(serializers.Serializer):
    restaurant = PublicMenuRestaurantSerializer()
    table = PublicMenuTableSerializer()
    categories = PublicMenuCategorySerializer(many=True)
    items = PublicMenuItemSerializer(many=True)


# =============================================================================
# Common responses / errors
# =============================================================================

class APIErrorSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    error_code = serializers.CharField(required=False, allow_blank=True)


class APISuccessSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()


class IDResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField(required=False)
    id = serializers.IntegerField(required=False)


# =============================================================================
# Orders
# =============================================================================

class OrderIDPathSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()


class OrderCancelRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class OrderPayloadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order_number = serializers.CharField()
    status = serializers.CharField()
    payment_status = serializers.CharField()
    order_type = serializers.CharField()
    delivery_status = serializers.CharField(allow_null=True, required=False)
    kitchen_printed = serializers.BooleanField()
    receipt_printed = serializers.BooleanField()
    is_completed = serializers.BooleanField()
    cancelled_at = serializers.DateTimeField(allow_null=True, required=False)


class OrderCancelResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True)
    order = OrderPayloadSerializer()


class OrderPrintStatusRequestSerializer(serializers.Serializer):
    kitchen_printed = serializers.BooleanField(required=False)
    receipt_printed = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Provide kitchen_printed and/or receipt_printed."
            )
        return attrs


class OrderPrintStatusResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    order = OrderPayloadSerializer()


class AssignDeliveryPartnerRequestSerializer(serializers.Serializer):
    delivery_partner = serializers.IntegerField()


class AssignDeliveryPartnerResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    order = OrderPayloadSerializer()
    partner = serializers.DictField()


class UnassignDeliveryPartnerResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    order = OrderPayloadSerializer()


class DeliveryStatusRequestSerializer(serializers.Serializer):
    delivery_status = serializers.CharField()


class DeliveryStatusResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    order = OrderPayloadSerializer()


class DeliveryTrackingSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=False)
    order_number = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    delivery_status = serializers.CharField(required=False, allow_null=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class DeliveryTrackingResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    tracking = DeliveryTrackingSerializer(required=False)


# =============================================================================
# Restaurant location / fulfillment
# =============================================================================

class RestaurantLocationSerializer(serializers.Serializer):
    latitude = serializers.FloatField(allow_null=True, required=False)
    longitude = serializers.FloatField(allow_null=True, required=False)
    city = serializers.CharField(allow_blank=True, required=False)
    state = serializers.CharField(allow_blank=True, required=False)
    country = serializers.CharField(allow_blank=True, required=False)
    pincode = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)


class RestaurantLocationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    location = RestaurantLocationSerializer()


class RestaurantLocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    pincode = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class DeliverySummarySerializer(serializers.Serializer):
    can_deliver = serializers.BooleanField()
    distance_km = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivery_charge = serializers.DecimalField(max_digits=12, decimal_places=2)
    estimated_minutes = serializers.IntegerField()
    free_delivery = serializers.BooleanField()


class PickupOptionsSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    cash_on_pickup = serializers.BooleanField()


class DeliverySummaryResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    delivery = DeliverySummarySerializer()
    pickup = PickupOptionsSerializer()


class FulfillmentOptionsSerializer(serializers.Serializer):
    dinein = serializers.BooleanField()
    pickup = serializers.BooleanField()
    delivery = serializers.BooleanField()
    cash_on_pickup = serializers.BooleanField()
    cash_on_delivery = serializers.BooleanField()
    minimum_delivery_order = serializers.DecimalField(max_digits=12, decimal_places=2)
    free_delivery_radius_km = serializers.DecimalField(max_digits=12, decimal_places=2)
    maximum_delivery_radius_km = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivery_charge_per_km = serializers.DecimalField(max_digits=12, decimal_places=2)


class FulfillmentOptionsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    options = FulfillmentOptionsSerializer()


# =============================================================================
# Delivery partners
# =============================================================================

class DeliveryPartnerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField(allow_blank=True, required=False)
    full_name = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField(allow_blank=True, required=False)
    vehicle_type = serializers.CharField(allow_blank=True, required=False)
    vehicle_number = serializers.CharField(allow_blank=True, required=False)
    is_active = serializers.BooleanField()
    is_available = serializers.BooleanField()
    is_verified = serializers.BooleanField()
    latitude = serializers.FloatField(allow_null=True, required=False)
    longitude = serializers.FloatField(allow_null=True, required=False)
    last_location_update = serializers.DateTimeField(allow_null=True, required=False)


class DeliveryPartnerCreateRequestSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    country_code = serializers.CharField(required=False, allow_blank=True, max_length=10)
    phone = serializers.CharField(max_length=30)
    alternate_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    pincode = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vehicle_type = serializers.CharField(required=False, allow_blank=True)
    vehicle_number = serializers.CharField(required=False, allow_blank=True)
    driving_license_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class DeliveryPartnerUpdateRequestSerializer(DeliveryPartnerCreateRequestSerializer):
    first_name = serializers.CharField(required=False, max_length=150)
    phone = serializers.CharField(required=False, max_length=30)
    is_active = serializers.BooleanField(required=False)
    is_verified = serializers.BooleanField(required=False)


class DeliveryPartnerResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    delivery_partner = DeliveryPartnerSerializer()


class DeliveryPartnerListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    count = serializers.IntegerField()
    delivery_partners = DeliveryPartnerSerializer(many=True)


class DeliveryPartnerAvailabilityRequestSerializer(serializers.Serializer):
    is_available = serializers.BooleanField()


class DeliveryPartnerAvailabilityResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    is_available = serializers.BooleanField()


class DeliveryPartnerLocationRequestSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class DeliveryPartnerLocationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    partner_id = serializers.IntegerField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    updated_at = serializers.DateTimeField()


class DeliveryPartnerDeleteResponseSerializer(APISuccessSerializer):
    pass


# =============================================================================
# Inventory
# =============================================================================

class InventoryItemSerializer(serializers.ModelSerializer):
    food_item = serializers.IntegerField(source="food_item_id", allow_null=True, read_only=True)
    low_stock = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "restaurant",
            "food_item",
            "name",
            "sku",
            "unit",
            "quantity",
            "reorder_level",
            "cost_price",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
            "low_stock",
        ]
        read_only_fields = ["id", "restaurant", "created_at", "updated_at", "low_stock"]

    def get_low_stock(self, obj):
        return obj.quantity <= obj.reorder_level


class InventoryCreateRequestSerializer(serializers.Serializer):
    food_item = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    sku = serializers.CharField(required=False, allow_blank=True, max_length=80)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=30)
    quantity = serializers.DecimalField(required=False, max_digits=12, decimal_places=3)
    reorder_level = serializers.DecimalField(required=False, max_digits=12, decimal_places=3)
    cost_price = serializers.DecimalField(required=False, max_digits=12, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)


class InventoryUpdateRequestSerializer(serializers.Serializer):
    food_item = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    sku = serializers.CharField(required=False, allow_blank=True, max_length=80)
    unit = serializers.CharField(required=False, allow_blank=True, max_length=30)
    quantity = serializers.DecimalField(required=False, max_digits=12, decimal_places=3)
    reorder_level = serializers.DecimalField(required=False, max_digits=12, decimal_places=3)
    cost_price = serializers.DecimalField(required=False, max_digits=12, decimal_places=2)
    is_active = serializers.BooleanField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class InventoryListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    count = serializers.IntegerField()
    inventory = InventoryItemSerializer(many=True)


class InventoryCreateResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    inventory_id = serializers.IntegerField()


class InventoryUpdateResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    inventory_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    low_stock = serializers.BooleanField()


class InventoryDeleteResponseSerializer(APISuccessSerializer):
    pass


# =============================================================================
# Coupons
# =============================================================================

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id",
            "restaurant",
            "code",
            "discount_type",
            "value",
            "minimum_order_amount",
            "maximum_discount",
            "usage_limit",
            "used_count",
            "valid_from",
            "valid_until",
            "applies_to_dinein",
            "applies_to_pickup",
            "applies_to_delivery",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "restaurant", "used_count", "created_at", "updated_at"]


class CouponCreateRequestSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    discount_type = serializers.ChoiceField(choices=["percent", "fixed"])
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_amount = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    maximum_discount = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=2)
    usage_limit = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    valid_from = serializers.DateTimeField(required=False, allow_null=True)
    valid_until = serializers.DateTimeField(required=False, allow_null=True)
    applies_to_dinein = serializers.BooleanField(required=False)
    applies_to_pickup = serializers.BooleanField(required=False)
    applies_to_delivery = serializers.BooleanField(required=False)


class CouponUpdateRequestSerializer(CouponCreateRequestSerializer):
    code = serializers.CharField(required=False, max_length=50)
    discount_type = serializers.ChoiceField(required=False, choices=["percent", "fixed"])
    value = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)


class CouponListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    count = serializers.IntegerField()
    coupons = CouponSerializer(many=True)


class CouponResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    coupon = CouponSerializer()


class CouponDeleteResponseSerializer(APISuccessSerializer):
    pass


class CouponValidateRequestSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    order_type = serializers.ChoiceField(choices=["dinein", "pickup", "delivery"], required=False)


class CouponValidationResultSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    message = serializers.CharField(required=False)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    coupon = CouponSerializer(required=False)


class CouponValidateResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    validation = CouponValidationResultSerializer(required=False)
    coupon = CouponSerializer(required=False)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    message = serializers.CharField(required=False)


# =============================================================================
# Reviews
# =============================================================================

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = [
            "id",
            "restaurant",
            "order",
            "customer_name",
            "customer_email",
            "rating",
            "comment",
            "owner_response",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "restaurant", "created_at", "updated_at"]


class ReviewCreateRequestSerializer(serializers.Serializer):
    order = serializers.IntegerField(required=False, allow_null=True)
    customer_name = serializers.CharField(max_length=120)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)
    owner_response = serializers.CharField(required=False, allow_blank=True)
    is_published = serializers.BooleanField(required=False)


class ReviewUpdateRequestSerializer(serializers.Serializer):
    customer_name = serializers.CharField(required=False, max_length=120)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    rating = serializers.IntegerField(required=False, min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)
    owner_response = serializers.CharField(required=False, allow_blank=True)
    is_published = serializers.BooleanField(required=False)


class ReviewListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    count = serializers.IntegerField()
    reviews = ReviewSerializer(many=True)


class ReviewResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    review = ReviewSerializer()


# =============================================================================
# Reports
# =============================================================================

class RestaurantStatisticsSerializer(serializers.Serializer):
    orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    categories = serializers.IntegerField()
    food_items = serializers.IntegerField()
    tables = serializers.IntegerField()
    staff = serializers.IntegerField()
    delivery_partners = serializers.IntegerField()


class SalesStatisticsSerializer(serializers.Serializer):
    total_sales = serializers.DecimalField(max_digits=18, decimal_places=2)
    average_order = serializers.DecimalField(max_digits=18, decimal_places=2)
    paid_orders = serializers.IntegerField()


class PeriodSalesSerializer(serializers.Serializer):
    today = serializers.DecimalField(max_digits=18, decimal_places=2)
    last_7_days = serializers.DecimalField(max_digits=18, decimal_places=2)
    month = serializers.DecimalField(max_digits=18, decimal_places=2)
    year = serializers.DecimalField(max_digits=18, decimal_places=2)


class OrderStatisticsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    pending = serializers.IntegerField()
    confirmed = serializers.IntegerField()
    preparing = serializers.IntegerField()
    ready = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()


class MenuStatisticsSerializer(serializers.Serializer):
    categories = serializers.IntegerField()
    food_items = serializers.IntegerField()
    available_items = serializers.IntegerField()
    paused_items = serializers.IntegerField()


class StaffStatisticsSerializer(serializers.Serializer):
    total_staff = serializers.IntegerField()
    active_staff = serializers.IntegerField()
    on_shift = serializers.IntegerField()
    on_break = serializers.IntegerField()


class DeliveryStatisticsSerializer(serializers.Serializer):
    delivery_enabled = serializers.BooleanField()
    partners = serializers.IntegerField()
    available_partners = serializers.IntegerField()
    delivery_orders = serializers.IntegerField()
    delivered = serializers.IntegerField()


class CustomerStatisticsSerializer(serializers.Serializer):
    unique_customers = serializers.IntegerField()
    repeat_orders = serializers.IntegerField()


class TopSellingItemSerializer(serializers.Serializer):
    food_item = serializers.IntegerField()
    food_item__name = serializers.CharField()
    quantity_sold = serializers.IntegerField()


class ReportSerializer(serializers.Serializer):
    restaurant = RestaurantStatisticsSerializer()
    sales = SalesStatisticsSerializer()
    period_sales = PeriodSalesSerializer()
    orders = OrderStatisticsSerializer()
    menu = MenuStatisticsSerializer()
    staff = StaffStatisticsSerializer()
    delivery = DeliveryStatisticsSerializer()
    customers = CustomerStatisticsSerializer()
    top_selling_items = TopSellingItemSerializer(many=True)


class ReportsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    report = ReportSerializer()
