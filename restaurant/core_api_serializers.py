"""Explicit OpenAPI serializers for the legacy/core APIView endpoints.

These serializers document the response/request dictionaries assembled directly
inside restaurant.views.views without changing runtime API behaviour.
"""

from rest_framework import serializers


class CategoryPayloadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class CategoryListResponseSerializer(serializers.ListSerializer):
    child = CategoryPayloadSerializer()


class CategoryCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)


class CategoryResponseSerializer(CategoryPayloadSerializer):
    pass


class CategorySuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()


class MenuItemPayloadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    price = serializers.FloatField()
    description = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    category = serializers.IntegerField(allow_null=True, required=False)
    is_available = serializers.BooleanField()
    image = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class MenuItemListResponseSerializer(serializers.ListSerializer):
    child = MenuItemPayloadSerializer()


class MenuItemCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.IntegerField()
    image = serializers.ImageField(required=False, allow_null=True)


class MenuItemUpdateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=255)
    price = serializers.DecimalField(required=False, max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.IntegerField(required=False)
    is_available = serializers.BooleanField(required=False)
    image = serializers.ImageField(required=False, allow_null=True)


class MenuItemCreateResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    id = serializers.IntegerField()


class MenuItemResponseSerializer(MenuItemPayloadSerializer):
    pass


class PublicOrderDetailResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    table = serializers.IntegerField(allow_null=True)
    total = serializers.FloatField()


class TablePayloadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    table_number = serializers.IntegerField()
    qr_code = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class TableListResponseSerializer(serializers.ListSerializer):
    child = TablePayloadSerializer()


class TableCreateRequestSerializer(serializers.Serializer):
    table_number = serializers.IntegerField()


class TableCreateResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    id = serializers.IntegerField()
    table_number = serializers.IntegerField()
    qr_code = serializers.CharField()
    qr_url = serializers.CharField()


class RestaurantProfilePayloadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    cuisine = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    address = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    phone = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    about = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    logo = serializers.CharField(allow_null=True, required=False)
    logo_url = serializers.CharField(allow_null=True, required=False)
    cover_image = serializers.CharField(allow_null=True, required=False)
    cover_image_url = serializers.CharField(allow_null=True, required=False)


class SubscriptionSummarySerializer(serializers.Serializer):
    plan = serializers.CharField(allow_null=True, required=False)
    is_active = serializers.BooleanField()
    table_limit = serializers.IntegerField(allow_null=True, required=False)


class RestaurantProfileResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    restaurant = RestaurantProfilePayloadSerializer(allow_null=True)
    subscription = SubscriptionSummarySerializer(allow_null=True)


class RestaurantProfileRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True)
    cuisine = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    about = serializers.CharField(required=False, allow_blank=True)
    logo = serializers.ImageField(required=False, allow_null=True)
    cover_image = serializers.ImageField(required=False, allow_null=True)


class RestaurantProfileSaveResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    restaurant = RestaurantProfilePayloadSerializer()


class AIImageSearchResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    image_url = serializers.CharField(allow_blank=True, required=False)
    error = serializers.CharField(required=False, allow_blank=True)


class AIMenuItemSerializer(serializers.Serializer):
    category = serializers.CharField()
    item_name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    veg_or_nonveg = serializers.CharField(allow_blank=True, required=False)
    price = serializers.FloatField()
    confidence = serializers.FloatField(required=False)
    image_search_term = serializers.CharField(required=False, allow_blank=True)
    image_search_terms = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class AIMenuExtractRequestSerializer(serializers.Serializer):
    file = serializers.FileField()


class AIMenuExtractResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    items = AIMenuItemSerializer(many=True, required=False)
    error = serializers.CharField(required=False, allow_blank=True)


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField(required=False)
    detail = serializers.CharField(required=False)
    success = serializers.BooleanField(required=False)
    message = serializers.CharField(required=False)
    errors = serializers.DictField(required=False)


class DashboardResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
