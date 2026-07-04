# =============================================================================
# Django Imports
# =============================================================================
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

# =============================================================================
# Django REST Framework Imports
# =============================================================================

from rest_framework import serializers

from payments.services import calculate_discount, calculate_grand_total, calculate_packing_charge, calculate_subtotal, calculate_tax, update_order_totals
from restaurant.services import calculate_delivery_charge

# =============================================================================
# Local Application Imports
# =============================================================================

from .models import (
    Restaurant,
    Order,
    OrderItem,
    FoodItem,
    AddOn,
    Category,
)


# ================= RESTAURANT =================


# class RestaurantSerializer(serializers.ModelSerializer):

#     logo_url = serializers.SerializerMethodField()

#     cover_image_url = serializers.SerializerMethodField()

#     class Meta:

#         model = Restaurant

#         fields = [
#             'id',
#             'owner',
#             'name',
#             'address',
#             'about',
#             'cover_image',
#             'cover_image_url',
#             'logo',
#             'logo_url',
#             'phone',
#             'cuisine_type',
#             "delivery_enabled",
#             "pickup_enabled",
#             "delivery_latitude",
#             "delivery_longitude",
#             "free_delivery_radius_km",
#             "maximum_delivery_radius_km",
#             "delivery_charge_per_km",
#             "minimum_delivery_order",
#             "payment_enabled"
#             "delivery_enabled"
#             "accept_online"
#             "cash_on_delivery"
#             "cash_on_pickup"
#             "pickup_enabled"
#             "currency_code"
#             "currency_symbol"
#             "phone_country_code"
#             "email"
#             "website"
#         ]

#         read_only_fields = ['owner']

"""
===============================================================================
restaurant/serializers.py

Enterprise Restaurant Serializers

This module contains all serializers used by the Restaurant application.

Contents

    • RestaurantSerializer
    • FoodItemSerializer
    • OrderItemSerializer
    • CategorySerializer
    • OrderSerializer
    • RestaurantDeliverySerializer
    • RestaurantLocationSerializer
    • NearbyRestaurantSerializer
    • OrderDeliverySerializer
    • DeliveryValidationSerializer

The RestaurantSerializer is the primary serializer used for
Restaurant CRUD operations.

Features

    • Complete Restaurant model support
    • Image upload support
    • Absolute image URLs
    • Enterprise validation
    • Delivery configuration
    • Tax configuration
    • Currency configuration

===============================================================================
"""
# =============================================================================
# Restaurant Serializer
# =============================================================================


class RestaurantSerializer(serializers.ModelSerializer):
    """
    Enterprise serializer for Restaurant.

    Responsibilities

        • Restaurant CRUD

        • Image upload

        • Delivery configuration

        • Tax configuration

        • Currency configuration

        • Contact information

        • Location information
    """

    # =========================================================================
    # Computed Fields
    # =========================================================================

    logo_url = serializers.SerializerMethodField()

    cover_image_url = serializers.SerializerMethodField()

    # =========================================================================
    # Meta
    # =========================================================================

    class Meta:

        model = Restaurant

        fields = [

            # ===============================================================
            # Identity
            # ===============================================================

            "id",

            "owner",

            # ===============================================================
            # Basic Information
            # ===============================================================

            "name",

            "about",

            "address",

            "city",

            "state",

            "country",

            "pincode",

            "cuisine_type",

            # ===============================================================
            # Images
            # ===============================================================

            "logo",

            "logo_url",

            "cover_image",

            "cover_image_url",

            # ===============================================================
            # Contact Information
            # ===============================================================

            "phone_country_code",

            "phone",

            "alternate_phone",

            "email",

            "website",

            # ===============================================================
            # Tax Configuration
            # ===============================================================

            "tax_enabled",

            "tax_name",

            "tax_percentage",

            "prices_include_tax",

            "tax_registration_number",

            "fssai_number",

            "cgst_percentage",

            "sgst_percentage",

            "igst_percentage",

            # ===============================================================
            # Invoice Configuration
            # ===============================================================

            "invoice_prefix",

            "currency_code",

            "currency_symbol",

            "currency_decimal_places",

            "footer_message",

            "timezone",

            # ===============================================================
            # Payment Configuration
            # ===============================================================

            "default_payment_gateway",

            # ===============================================================
            # Delivery Configuration
            # ===============================================================

            "delivery_enabled",

            "pickup_enabled",

            "cash_on_delivery",

            "cash_on_pickup",

            "delivery_latitude",

            "delivery_longitude",

            "free_delivery_radius_km",

            "maximum_delivery_radius_km",

            "delivery_charge_per_km",

            "minimum_delivery_order",

            "average_preparation_time",

        ]

        read_only_fields = [

            "id",

            "owner",

            "logo_url",

            "cover_image_url",

        ]

        extra_kwargs = {

            "about": {
                "required": False,
            },

            "logo": {
                "required": False,
                "allow_null": True,
            },

            "cover_image": {
                "required": False,
                "allow_null": True,
            },

            "alternate_phone": {
                "required": False,
                "allow_blank": True,
            },

            "email": {
                "required": False,
                "allow_blank": True,
            },

            "website": {
                "required": False,
                "allow_blank": True,
            },

            "tax_registration_number": {
                "required": False,
                "allow_blank": True,
            },

            "fssai_number": {
                "required": False,
                "allow_blank": True,
            },

            "footer_message": {
                "required": False,
                "allow_blank": True,
            },

            "delivery_latitude": {
                "required": False,
                "allow_null": True,
            },

            "delivery_longitude": {
                "required": False,
                "allow_null": True,
            },

        }
        
        
    # =========================================================================
    # Field Validation
    # =========================================================================

    # -------------------------------------------------------------------------
    # Restaurant Name
    # -------------------------------------------------------------------------

    def validate_name(self, value):
        """
        Validate restaurant name.
        """

        value = value.strip()

        if len(value) < 2:

            raise serializers.ValidationError(
                "Restaurant name is too short."
            )

        if len(value) > 100:

            raise serializers.ValidationError(
                "Restaurant name cannot exceed 100 characters."
            )

        return value

    # -------------------------------------------------------------------------
    # Phone Number
    # -------------------------------------------------------------------------

    def validate_phone(self, value):
        """
        Validate primary phone number.
        """

        value = value.strip()

        if not value:

            raise serializers.ValidationError(
                "Phone number is required."
            )

        digits = "".join(
            c for c in value
            if c.isdigit()
        )

        if len(digits) < 8:

            raise serializers.ValidationError(
                "Invalid phone number."
            )

        return value

    # -------------------------------------------------------------------------
    # Alternate Phone
    # -------------------------------------------------------------------------

    def validate_alternate_phone(self, value):
        """
        Validate alternate phone.
        """

        if not value:
            return value

        digits = "".join(
            c for c in value
            if c.isdigit()
        )

        if len(digits) < 8:

            raise serializers.ValidationError(
                "Invalid alternate phone number."
            )

        return value

    # -------------------------------------------------------------------------
    # Email
    # -------------------------------------------------------------------------

    def validate_email(self, value):
        """
        Normalize email.
        """

        if not value:

            return value

        return value.strip().lower()

    # -------------------------------------------------------------------------
    # Website
    # -------------------------------------------------------------------------

    def validate_website(self, value):
        """
        Validate website URL.
        """

        if not value:

            return value

        value = value.strip()

        if not (
            value.startswith("http://")
            or
            value.startswith("https://")
        ):

            raise serializers.ValidationError(
                "Website must begin with http:// or https://"
            )

        return value

    # -------------------------------------------------------------------------
    # Latitude
    # -------------------------------------------------------------------------

    def validate_delivery_latitude(self, value):
        """
        Validate restaurant latitude.
        """

        if value is None:

            return value

        if value < Decimal("-90"):

            raise serializers.ValidationError(
                "Latitude cannot be less than -90."
            )

        if value > Decimal("90"):

            raise serializers.ValidationError(
                "Latitude cannot exceed 90."
            )

        return value

    # -------------------------------------------------------------------------
    # Longitude
    # -------------------------------------------------------------------------

    def validate_delivery_longitude(self, value):
        """
        Validate restaurant longitude.
        """

        if value is None:

            return value

        if value < Decimal("-180"):

            raise serializers.ValidationError(
                "Longitude cannot be less than -180."
            )

        if value > Decimal("180"):

            raise serializers.ValidationError(
                "Longitude cannot exceed 180."
            )

        return value

    # -------------------------------------------------------------------------
    # Tax Percentage
    # -------------------------------------------------------------------------

    def validate_tax_percentage(self, value):
        """
        Validate overall tax percentage.
        """

        if value < Decimal("0"):

            raise serializers.ValidationError(
                "Tax percentage cannot be negative."
            )

        if value > Decimal("100"):

            raise serializers.ValidationError(
                "Tax percentage cannot exceed 100%."
            )

        return value

    # -------------------------------------------------------------------------
    # CGST
    # -------------------------------------------------------------------------

    def validate_cgst_percentage(self, value):

        if value < Decimal("0"):

            raise serializers.ValidationError(
                "CGST cannot be negative."
            )

        return value

    # -------------------------------------------------------------------------
    # SGST
    # -------------------------------------------------------------------------

    def validate_sgst_percentage(self, value):

        if value < Decimal("0"):

            raise serializers.ValidationError(
                "SGST cannot be negative."
            )

        return value

    # -------------------------------------------------------------------------
    # IGST
    # -------------------------------------------------------------------------

    def validate_igst_percentage(self, value):

        if value < Decimal("0"):

            raise serializers.ValidationError(
                "IGST cannot be negative."
            )

        return value

    # -------------------------------------------------------------------------
    # Free Delivery Radius
    # -------------------------------------------------------------------------

    def validate_free_delivery_radius_km(self, value):

        if value < Decimal("0"):

            raise serializers.ValidationError(
                "Free delivery radius cannot be negative."
            )

        return value

    # -------------------------------------------------------------------------
    # Maximum Delivery Radius
    # -------------------------------------------------------------------------

    def validate_maximum_delivery_radius_km(self, value):

        if value <= Decimal("0"):

            raise serializers.ValidationError(
                "Maximum delivery radius must be greater than zero."
            )

        return value

    # -------------------------------------------------------------------------
    # Delivery Charge
    # -------------------------------------------------------------------------

    def validate_delivery_charge_per_km(self, value):

        if value < Decimal("0"):

            raise serializers.ValidationError(
                "Delivery charge cannot be negative."
            )

        return value

    # -------------------------------------------------------------------------
    # Minimum Delivery Order
    # -------------------------------------------------------------------------

    def validate_minimum_delivery_order(self, value):

        if value < Decimal("0"):

            raise serializers.ValidationError(
                "Minimum delivery order cannot be negative."
            )

        return value

    # -------------------------------------------------------------------------
    # Average Preparation Time
    # -------------------------------------------------------------------------

    def validate_average_preparation_time(self, value):

        if value <= 0:

            raise serializers.ValidationError(
                "Preparation time must be greater than zero."
            )

        return value

    # =========================================================================
    # Object Validation
    # =========================================================================

    def validate(self, attrs):
        """
        Cross-field validation.
        """

        free_radius = attrs.get(
            "free_delivery_radius_km",
            getattr(
                self.instance,
                "free_delivery_radius_km",
                Decimal("0.00"),
            )
            if self.instance else Decimal("0.00"),
        )

        maximum_radius = attrs.get(
            "maximum_delivery_radius_km",
            getattr(
                self.instance,
                "maximum_delivery_radius_km",
                Decimal("0.00"),
            )
            if self.instance else Decimal("0.00"),
        )

        delivery_enabled = attrs.get(
            "delivery_enabled",
            getattr(
                self.instance,
                "delivery_enabled",
                False,
            )
            if self.instance else False,
        )

        latitude = attrs.get(
            "delivery_latitude",
            getattr(
                self.instance,
                "delivery_latitude",
                None,
            )
            if self.instance else None,
        )

        longitude = attrs.get(
            "delivery_longitude",
            getattr(
                self.instance,
                "delivery_longitude",
                None,
            )
            if self.instance else None,
        )

        # --------------------------------------------------------------
        # Radius Validation
        # --------------------------------------------------------------

        if free_radius > maximum_radius:

            raise serializers.ValidationError(

                {
                    "free_delivery_radius_km":
                        (
                            "Free delivery radius "
                            "cannot exceed maximum radius."
                        )
                }

            )

        # --------------------------------------------------------------
        # Delivery Location
        # --------------------------------------------------------------

        if delivery_enabled:

            if latitude is None:

                raise serializers.ValidationError(

                    {
                        "delivery_latitude":
                            (
                                "Restaurant latitude "
                                "is required."
                            )
                    }

                )

            if longitude is None:

                raise serializers.ValidationError(

                    {
                        "delivery_longitude":
                            (
                                "Restaurant longitude "
                                "is required."
                            )
                    }

                )

        # --------------------------------------------------------------
        # GST Validation
        # --------------------------------------------------------------

        cgst = attrs.get(
            "cgst_percentage",
            getattr(
                self.instance,
                "cgst_percentage",
                Decimal("0.00"),
            )
            if self.instance else Decimal("0.00"),
        )

        sgst = attrs.get(
            "sgst_percentage",
            getattr(
                self.instance,
                "sgst_percentage",
                Decimal("0.00"),
            )
            if self.instance else Decimal("0.00"),
        )

        igst = attrs.get(
            "igst_percentage",
            getattr(
                self.instance,
                "igst_percentage",
                Decimal("0.00"),
            )
            if self.instance else Decimal("0.00"),
        )

        tax = attrs.get(
            "tax_percentage",
            getattr(
                self.instance,
                "tax_percentage",
                Decimal("0.00"),
            )
            if self.instance else Decimal("0.00"),
        )

        if abs((cgst + sgst) - igst) > Decimal("0.01"):

            raise serializers.ValidationError(

                {
                    "igst_percentage":
                        (
                            "IGST should normally equal "
                            "CGST + SGST."
                        )
                }

            )

        if tax != igst:

            raise serializers.ValidationError(

                {
                    "tax_percentage":
                        (
                            "Tax percentage should match "
                            "the IGST percentage."
                        )
                }

            )

        return attrs
    
    
    # =========================================================================
    # Logo URL
    # =========================================================================

    def get_logo_url(self, obj):
        """
        Return an absolute URL for the restaurant logo.

        If the serializer has access to the current request,
        build an absolute URL.

        Otherwise return the relative media URL.
        """

        if not obj.logo:
            return None

        request = self.context.get("request")

        try:

            if request:

                return request.build_absolute_uri(
                    obj.logo.url
                )

            return obj.logo.url

        except Exception:

            return None

    # =========================================================================
    # Cover Image URL
    # =========================================================================

    def get_cover_image_url(self, obj):
        """
        Return an absolute URL for the restaurant cover image.
        """

        if not obj.cover_image:
            return None

        request = self.context.get("request")

        try:

            if request:

                return request.build_absolute_uri(
                    obj.cover_image.url
                )

            return obj.cover_image.url

        except Exception:

            return None

    # =========================================================================
    # Update Restaurant
    # =========================================================================

    def update(
        self,
        instance,
        validated_data,
    ):
        """
        Update an existing restaurant.

        Responsibilities

            • Update normal model fields

            • Replace logo

            • Replace cover image

            • Preserve default images

            • Save model

            • Refresh instance

        Returns
        -------
        Restaurant
        """

        request = self.context.get(
            "request"
        )

        # ==============================================================
        # Uploaded Files
        # ==============================================================

        logo = None

        cover_image = None

        if request:

            logo = request.FILES.get(
                "logo"
            )

            cover_image = request.FILES.get(
                "cover_image"
            )

        # ==============================================================
        # Remove File Fields
        #
        # Prevent DRF from attempting to assign uploaded
        # files twice.
        # ==============================================================

        validated_data.pop(
            "logo",
            None,
        )

        validated_data.pop(
            "cover_image",
            None,
        )

        # ==============================================================
        # Update Normal Fields
        # ==============================================================

        for field, value in validated_data.items():

            setattr(
                instance,
                field,
                value,
            )

        # ==============================================================
        # Replace Logo
        # ==============================================================

        if logo:

            old_logo = instance.logo

            if (
                old_logo
                and
                "default/" not in str(old_logo)
            ):

                try:

                    old_logo.delete(
                        save=False
                    )

                except Exception:
                    pass

            instance.logo = logo

        # ==============================================================
        # Replace Cover Image
        # ==============================================================

        if cover_image:

            old_cover = instance.cover_image

            if (
                old_cover
                and
                "default/" not in str(old_cover)
            ):

                try:

                    old_cover.delete(
                        save=False
                    )

                except Exception:
                    pass

            instance.cover_image = cover_image

        # ==============================================================
        # Save Restaurant
        # ==============================================================

        instance.save()

        # ==============================================================
        # Refresh Instance
        # ==============================================================

        instance.refresh_from_db()

        return instance

    # =====================================================
    # LOGO URL
    # =====================================================

    # def get_logo_url(self, obj):

    #     request = self.context.get('request')

    #     if not obj.logo:
    #         return None

    #     try:

    #         if request:
    #             return request.build_absolute_uri(
    #                 obj.logo.url
    #             )

    #         return obj.logo.url

    #     except Exception as e:

    #         print("LOGO URL ERROR:", str(e))

    #         return None

    # =====================================================
    # COVER IMAGE URL
    # =====================================================

    # def get_cover_image_url(self, obj):

    #     request = self.context.get('request')

    #     if not obj.cover_image:
    #         return None

    #     try:

    #         if request:
    #             return request.build_absolute_uri(
    #                 obj.cover_image.url
    #             )

    #         return obj.cover_image.url

    #     except Exception as e:

    #         print("COVER URL ERROR:", str(e))

    #         return None

    # =====================================================
    # UPDATE
    # =====================================================

    # def update(self, instance, validated_data):

    #     request = self.context.get('request', None)

    #     if request:
    #         print("FILES:", request.FILES)

    #     # =====================================================
    #     # REMOVE FILE FIELDS FROM VALIDATED DATA
    #     # IMPORTANT FIX
    #     # =====================================================

    #     validated_data.pop('logo', None)

    #     validated_data.pop('cover_image', None)

    #     # =====================================================
    #     # HANDLE LOGO
    #     # =====================================================

    #     if request and request.FILES.get('logo'):

    #         new_logo = request.FILES.get('logo')

    #         if new_logo:

    #             # avoid deleting default image
    #             if (
    #                 instance.logo and
    #                 'default/' not in str(instance.logo)
    #             ):

    #                 try:
    #                     instance.logo.delete(save=False)
    #                 except Exception as e:
    #                     print(str(e))

    #             instance.logo = new_logo

    #     # =====================================================
    #     # HANDLE COVER IMAGE
    #     # =====================================================

    #     if request and request.FILES.get('cover_image'):

    #         new_cover = request.FILES.get(
    #             'cover_image'
    #         )

    #         if new_cover:

    #             if (
    #                 instance.cover_image and
    #                 'default/' not in str(instance.cover_image)
    #             ):

    #                 try:
    #                     instance.cover_image.delete(
    #                         save=False
    #                     )
    #                 except Exception as e:
    #                     print(str(e))

    #             instance.cover_image = new_cover

    #     # =====================================================
    #     # NORMAL TEXT FIELDS
    #     # =====================================================

    #     for attr, value in validated_data.items():

    #         setattr(instance, attr, value)

    #     instance.save()

    #     instance.refresh_from_db()

    #     return instance


# ================= FOOD ITEM ================= #


# class FoodItemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = FoodItem
#         fields = '__all__'   # OR explicitly add 'is_veg'

# =============================================================================
# Food Item Serializer
# =============================================================================

class FoodItemSerializer(serializers.ModelSerializer):
    """
    Enterprise serializer for Food Items.

    Responsibilities

        • Food Item CRUD

        • Image Upload

        • Image URL Generation

        • Price Validation

        • Restaurant Validation

        • Category Validation

        • Availability Management
    """

    # =========================================================================
    # Computed Fields
    # =========================================================================

    image_url = serializers.SerializerMethodField()

    # =========================================================================
    # Meta
    # =========================================================================

    class Meta:

        model = FoodItem

        fields = [

            # ===============================================================
            # Identity
            # ===============================================================

            "id",

            # ===============================================================
            # Relationships
            # ===============================================================

            "restaurant",

            "category",

            # ===============================================================
            # Basic Information
            # ===============================================================

            "name",

            "description",

            # ===============================================================
            # Pricing
            # ===============================================================

            "price",

            # ===============================================================
            # Images
            # ===============================================================

            "image",

            "image_url",

            # ===============================================================
            # Addons
            # ===============================================================

            "addons",

            # ===============================================================
            # Item Configuration
            # ===============================================================

            "is_veg",

            "is_paused",

        ]

        read_only_fields = [

            "id",

            "image_url",

        ]

        extra_kwargs = {

            "description": {

                "required": False,

                "allow_blank": True,

                "allow_null": True,

            },

            "image": {

                "required": False,

                "allow_null": True,

            },

            "addons": {

                "required": False,

            },

        }

    # =========================================================================
    # Image URL
    # =========================================================================

    def get_image_url(self, obj):
        """
        Returns absolute image URL.
        """

        if not obj.image:

            return None

        request = self.context.get(
            "request"
        )

        try:

            if request:

                return request.build_absolute_uri(
                    obj.image.url
                )

            return obj.image.url

        except Exception:

            return None

    # =========================================================================
    # Name
    # =========================================================================

    def validate_name(self, value):
        """
        Validate food item name.
        """

        value = value.strip()

        if len(value) < 2:

            raise serializers.ValidationError(

                "Food item name is too short."

            )

        if len(value) > 100:

            raise serializers.ValidationError(

                "Food item name cannot exceed 100 characters."

            )

        return value

    # =========================================================================
    # Price
    # =========================================================================

    def validate_price(self, value):
        """
        Validate selling price.
        """

        if value < Decimal("0.00"):

            raise serializers.ValidationError(

                "Price cannot be negative."

            )

        return value

    # =========================================================================
    # Description
    # =========================================================================

    def validate_description(self, value):
        """
        Normalize description.
        """

        if value is None:

            return value

        return value.strip()

    # =========================================================================
    # Category
    # =========================================================================

    def validate_category(self, value):
        """
        Ensure category belongs to the same restaurant.
        """

        restaurant = self.initial_data.get(
            "restaurant"
        )

        if restaurant:

            if str(value.restaurant_id) != str(restaurant):

                raise serializers.ValidationError(

                    "Category does not belong to this restaurant."

                )

        return value

    # =========================================================================
    # Object Validation
    # =========================================================================

    def validate(self, attrs):
        """
        Cross-field validation.
        """

        restaurant = attrs.get(

            "restaurant",

            getattr(
                self.instance,
                "restaurant",
                None,
            )

            if self.instance else None,

        )

        category = attrs.get(

            "category",

            getattr(
                self.instance,
                "category",
                None,
            )

            if self.instance else None,

        )

        if restaurant and category:

            if category.restaurant_id != restaurant.id:

                raise serializers.ValidationError(

                    {

                        "category":

                            "Category belongs to another restaurant."

                    }

                )

        return attrs

    # =========================================================================
    # Update
    # =========================================================================

    def update(
        self,
        instance,
        validated_data,
    ):
        """
        Update food item.

        Handles image replacement while preserving
        the default image.
        """

        request = self.context.get(
            "request"
        )

        image = None

        if request:

            image = request.FILES.get(
                "image"
            )

        validated_data.pop(
            "image",
            None,
        )

        for field, value in validated_data.items():

            setattr(
                instance,
                field,
                value,
            )

        if image:

            old_image = instance.image

            if (

                old_image

                and

                "default/" not in str(old_image)

            ):

                try:

                    old_image.delete(
                        save=False
                    )

                except Exception:
                    pass

            instance.image = image

        instance.save()

        instance.refresh_from_db()

        return instance


# ================= ORDER ITEM =================

# class OrderItemSerializer(serializers.ModelSerializer):
#     food_item_id = serializers.IntegerField(write_only=True)
#     selected_addons_ids = serializers.ListField(
#         child=serializers.IntegerField(),
#         write_only=True,
#         required=False
#     )

#     food_item_name = serializers.CharField(source='food_item.name', read_only=True)

#     is_veg = serializers.BooleanField(source='food_item.is_veg', read_only=True)

#     class Meta:
#         model = OrderItem
#         fields = [
#             'id',
#             'food_item_id',
#             'food_item_name',
#             'quantity',
#             'is_veg',
#             'selected_addons_ids',
#             'selected_addons'
#         ]
#         read_only_fields = ['selected_addons']



# =============================================================================
# Order Item Serializer
# =============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Enterprise serializer for Order Items.

    Responsibilities

        • Create Order Items

        • Update Order Items

        • Validate Food Item

        • Validate Quantity

        • Validate Addons

        • Prevent cross-restaurant items

        • Calculate readonly display fields
    """

    # =========================================================================
    # Input Fields
    # =========================================================================

    food_item_id = serializers.IntegerField(
        write_only=True
    )

    selected_addons_ids = serializers.ListField(

        child=serializers.IntegerField(),

        write_only=True,

        required=False,

        default=list,

    )

    # =========================================================================
    # Display Fields
    # =========================================================================

    food_item_name = serializers.CharField(

        source="food_item.name",

        read_only=True,

    )

    is_veg = serializers.BooleanField(

        source="food_item.is_veg",

        read_only=True,

    )

    price = serializers.DecimalField(

        source="food_item.price",

        max_digits=8,

        decimal_places=2,

        read_only=True,

    )

    addons = serializers.SerializerMethodField()

    line_total = serializers.SerializerMethodField()

    # =========================================================================
    # Meta
    # =========================================================================

    class Meta:

        model = OrderItem

        fields = [

            # ===============================================================
            # Identity
            # ===============================================================

            "id",

            # ===============================================================
            # Input
            # ===============================================================

            "food_item_id",

            "quantity",

            "selected_addons_ids",

            # ===============================================================
            # Display
            # ===============================================================

            "food_item_name",

            "price",

            "is_veg",

            "addons",

            "line_total",

            # ===============================================================
            # Relations
            # ===============================================================

            "selected_addons",

        ]

        read_only_fields = [

            "id",

            "food_item_name",

            "price",

            "is_veg",

            "addons",

            "line_total",

            "selected_addons",

        ]

    # =========================================================================
    # Quantity
    # =========================================================================

    def validate_quantity(
        self,
        value,
    ):

        if value <= 0:

            raise serializers.ValidationError(

                "Quantity must be greater than zero."

            )

        if value > 100:

            raise serializers.ValidationError(

                "Maximum quantity is 100."

            )

        return value

    # =========================================================================
    # Food Item
    # =========================================================================

    def validate_food_item_id(
        self,
        value,
    ):

        try:

            food = FoodItem.objects.get(
                id=value
            )

        except FoodItem.DoesNotExist:

            raise serializers.ValidationError(

                "Food item not found."

            )

        if food.is_paused:

            raise serializers.ValidationError(

                "Food item is currently unavailable."

            )

        return value

    # =========================================================================
    # Addons
    # =========================================================================

    def validate_selected_addons_ids(
        self,
        value,
    ):

        if len(value) != len(set(value)):

            raise serializers.ValidationError(

                "Duplicate addons are not allowed."

            )

        return value

    # =========================================================================
    # Object Validation
    # =========================================================================

    def validate(
        self,
        attrs,
    ):

        food_item = FoodItem.objects.get(

            id=attrs["food_item_id"]

        )

        addon_ids = attrs.get(

            "selected_addons_ids",

            [],

        )

        addons = AddOn.objects.filter(

            id__in=addon_ids

        )

        for addon in addons:

            if addon not in food_item.addons.all():

                raise serializers.ValidationError(

                    {

                        "selected_addons_ids":

                            f"{addon.name} is not available for this food item."

                    }

                )

        return attrs

    # =========================================================================
    # Addons
    # =========================================================================

    def get_addons(
        self,
        obj,
    ):

        return [

            {

                "id": addon.id,

                "name": addon.name,

                "price": addon.price,

            }

            for addon in obj.selected_addons.all()

        ]

    # =========================================================================
    # Line Total
    # =========================================================================

    def get_line_total(
        self,
        obj,
    ):

        base = (

            obj.food_item.price

            or Decimal("0.00")

        ) * obj.quantity

        addons_total = sum(

            (

                addon.price

                or Decimal("0.00")

            )

            for addon in obj.selected_addons.all()

        )

        addons_total *= obj.quantity

        return base + addons_total

    # =========================================================================
    # Create
    # =========================================================================

    def create(
        self,
        validated_data,
    ):

        addon_ids = validated_data.pop(

            "selected_addons_ids",

            [],

        )

        food_item = FoodItem.objects.get(

            id=validated_data.pop(

                "food_item_id"

            )

        )

        order_item = OrderItem.objects.create(

            food_item=food_item,

            **validated_data,

        )

        if addon_ids:

            addons = AddOn.objects.filter(

                id__in=addon_ids

            )

            order_item.selected_addons.set(

                addons

            )

        return order_item

    # =========================================================================
    # Update
    # =========================================================================

    def update(
        self,
        instance,
        validated_data,
    ):

        addon_ids = validated_data.pop(

            "selected_addons_ids",

            None,

        )

        food_item_id = validated_data.pop(

            "food_item_id",

            None,

        )

        if food_item_id is not None:

            instance.food_item = FoodItem.objects.get(

                id=food_item_id

            )

        for field, value in validated_data.items():

            setattr(

                instance,

                field,

                value,

            )

        instance.save()

        if addon_ids is not None:

            addons = AddOn.objects.filter(

                id__in=addon_ids

            )

            instance.selected_addons.set(

                addons

            )

        return instance

# =================== CATEGORY SERIALIZER ============== #

# class CategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Category
#         fields = ["id", "name"]




# =============================================================================
# Category Serializer
# =============================================================================

class CategorySerializer(serializers.ModelSerializer):
    """
    Enterprise serializer for Food Categories.

    Responsibilities

        • Category CRUD

        • Name Validation

        • Prevent duplicate category names
    """

    class Meta:

        model = Category

        fields = [

            "id",

            "restaurant",

            "name",

        ]

        read_only_fields = [

            "id",

        ]

    # =========================================================================
    # Name Validation
    # =========================================================================

    def validate_name(
        self,
        value,
    ):
        """
        Normalize category name.
        """

        value = value.strip()

        if len(value) < 2:

            raise serializers.ValidationError(

                "Category name is too short."

            )

        if len(value) > 100:

            raise serializers.ValidationError(

                "Category name cannot exceed 100 characters."

            )

        return value

    # =========================================================================
    # Object Validation
    # =========================================================================

    def validate(
        self,
        attrs,
    ):
        """
        Prevent duplicate category names within
        the same restaurant.
        """

        restaurant = attrs.get(
            "restaurant",
            getattr(
                self.instance,
                "restaurant",
                None,
            ) if self.instance else None,
        )

        name = attrs.get(
            "name",
            getattr(
                self.instance,
                "name",
                "",
            ) if self.instance else "",
        )

        queryset = Category.objects.filter(

            restaurant=restaurant,

            name__iexact=name,

        )

        if self.instance:

            queryset = queryset.exclude(
                id=self.instance.id
            )

        if queryset.exists():

            raise serializers.ValidationError(

                {
                    "name":
                        "A category with this name already exists."
                }

            )

        return attrs

# ================= ORDER =================

# class OrderSerializer(serializers.ModelSerializer):
#     items = OrderItemSerializer(many=True, write_only=True)
#     order_items = OrderItemSerializer(many=True, read_only=True)

#     class Meta:
#         model = Order
#         fields = [
#             'id',
#             'restaurant',
#             'table',
#             'customer_name',
#             'customer_phone',
#             'status',  # ✅ NOW WRITABLE
#             'is_completed',
#             'created_at',
#             'total_price_cached',
#             'items',
#             'order_items'
#         ]
#         # ❌ REMOVED status from read_only
#         read_only_fields = ['is_completed', 'created_at', 'total_price_cached']

#     # ================= CREATE =================
#     def create(self, validated_data):
#         items_data = validated_data.pop('items')

#         table = validated_data.get('table')
#         restaurant = table.restaurant

#         order = Order.objects.create(
#             table=table,
#             restaurant=restaurant,
#             customer_name=validated_data.get('customer_name', ''),
#             customer_phone=validated_data.get('customer_phone', '')
#         )

#         total = 0

#         for item in items_data:
#             food_item = FoodItem.objects.get(id=item['food_item_id'])
#             quantity = item.get('quantity', 1)

#             # 🔒 SECURITY CHECK
#             if food_item.restaurant != restaurant:
#                 raise serializers.ValidationError("Invalid food item for this restaurant")

#             order_item = OrderItem.objects.create(
#                 order=order,
#                 food_item=food_item,
#                 quantity=quantity
#             )

#             addon_ids = item.get('selected_addons_ids', [])
#             if addon_ids:
#                 addons = AddOn.objects.filter(id__in=addon_ids)
#                 order_item.selected_addons.set(addons)

#             base = (food_item.price or 0) * quantity
#             addons_price = sum(a.price for a in order_item.selected_addons.all()) * quantity
#             total += base + addons_price

#         order.total_price_cached = total
#         order.save()

#         return order

#     # ================= UPDATE (FIX FOR PATCH) =================
#     def update(self, instance, validated_data):
#         status = validated_data.get('status', instance.status)

#         instance.status = status

#         # ✅ SYNC BOOLEAN FIELD
#         if status == 'completed':
#             instance.is_completed = True
#         else:
#             instance.is_completed = False

#         instance.save()
#         return instance





# =============================================================================
# Order Serializer
# =============================================================================

class OrderSerializer(serializers.ModelSerializer):
    """
    Enterprise serializer for Orders.

    Responsibilities

        • Order Creation

        • Order Updates

        • Nested Order Items

        • Delivery Orders

        • Pickup Orders

        • Dine-In Orders

        • Payment Information

        • Customer Information

        • Tax Information

        • Order Totals
    """

    # =========================================================================
    # Nested Serializers
    # =========================================================================

    items = OrderItemSerializer(
        many=True,
        write_only=True,
        required=False,
    )

    order_items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    # =========================================================================
    # Meta
    # =========================================================================

    class Meta:

        model = Order

        fields = [

            # ===============================================================
            # Identity
            # ===============================================================

            "id",

            "order_number",

            # ===============================================================
            # Relationships
            # ===============================================================

            "restaurant",

            "table",

            # ===============================================================
            # Customer
            # ===============================================================

            "customer_name",

            "customer_phone",

            "customer_email",

            "customer_note",

            "customer_country",

            "customer_country_code",

            # ===============================================================
            # Order Type
            # ===============================================================

            "order_type",

            # ===============================================================
            # Delivery Address
            # ===============================================================

            "customer_address",

            "customer_city",

            "customer_state",

            "customer_pincode",

            "delivery_latitude",

            "delivery_longitude",

            # ===============================================================
            # Delivery Details
            # ===============================================================

            "delivery_distance_km",

            "delivery_charge",

            "delivery_status",

            "scheduled_time",

            "pickup_verified",

            "delivery_verified",

            "delivery_person_name",

            "delivery_person_phone",

            "assigned_at",

            "picked_at",

            "delivered_at",

            # ===============================================================
            # Status
            # ===============================================================

            "status",

            "payment_status",

            "is_completed",

            "created_at",

            "completed_at",

            # ===============================================================
            # Totals
            # ===============================================================

            "subtotal",

            "discount_amount",

            "tax_amount",

            "packing_charge",

            "tip_amount",

            "round_off",

            "grand_total",

            "cgst",

            "sgst",

            "igst",

            "total_price_cached",

            # ===============================================================
            # Printing
            # ===============================================================

            "kitchen_printed",

            "receipt_printed",

            # ===============================================================
            # Soft Delete
            # ===============================================================

            "is_deleted",

            # ===============================================================
            # Nested Items
            # ===============================================================

            "items",

            "order_items",

        ]

        read_only_fields = [

            # Identity

            "id",

            "order_number",

            # Completion

            "is_completed",

            "created_at",

            "completed_at",

            # Delivery Timeline

            "assigned_at",

            "picked_at",

            "delivered_at",

            # Calculated Values

            "delivery_distance_km",

            "subtotal",

            "discount_amount",

            "tax_amount",

            "packing_charge",

            "round_off",

            "grand_total",

            "cgst",

            "sgst",

            "igst",

            "total_price_cached",

            # Nested

            "order_items",

        ]

        extra_kwargs = {

            # ===========================================================
            # Customer
            # ===========================================================

            "customer_name": {

                "required": False,

                "allow_blank": True,

            },

            "customer_phone": {

                "required": False,

                "allow_blank": True,

            },

            "customer_email": {

                "required": False,

                "allow_blank": True,

            },

            "customer_note": {

                "required": False,

                "allow_blank": True,

            },

            # ===========================================================
            # Delivery Address
            # ===========================================================

            "customer_address": {

                "required": False,

                "allow_blank": True,

            },

            "customer_city": {

                "required": False,

                "allow_blank": True,

            },

            "customer_state": {

                "required": False,

                "allow_blank": True,

            },

            "customer_pincode": {

                "required": False,

                "allow_blank": True,

            },

            "delivery_latitude": {

                "required": False,

                "allow_null": True,

            },

            "delivery_longitude": {

                "required": False,

                "allow_null": True,

            },

            # ===========================================================
            # Delivery
            # ===========================================================

            "scheduled_time": {

                "required": False,

                "allow_null": True,

            },

            "delivery_person_name": {

                "required": False,

                "allow_blank": True,

            },

            "delivery_person_phone": {

                "required": False,

                "allow_blank": True,

            },

            # ===========================================================
            # Items
            # ===========================================================

            "items": {

                "required": True,

            },

        }
        
        
    # =========================================================================
    # Customer Name
    # =========================================================================

    def validate_customer_name(
        self,
        value,
    ):
        """
        Validate customer name.
        """

        value = value.strip()

        if len(value) < 2:

            raise serializers.ValidationError(

                "Customer name is too short."

            )

        if len(value) > 100:

            raise serializers.ValidationError(

                "Customer name cannot exceed 100 characters."

            )

        return value

    # =========================================================================
    # Customer Phone
    # =========================================================================

    def validate_customer_phone(
        self,
        value,
    ):
        """
        Validate customer phone.
        """

        if not value:

            return value

        value = value.strip()

        digits = "".join(

            c

            for c in value

            if c.isdigit()

        )

        if len(digits) < 8:

            raise serializers.ValidationError(

                "Invalid customer phone number."

            )

        return value

    # =========================================================================
    # Customer Email
    # =========================================================================

    def validate_customer_email(
        self,
        value,
    ):
        """
        Normalize customer email.
        """

        if not value:

            return value

        return value.strip().lower()

    # =========================================================================
    # Order Type
    # =========================================================================

    def validate_order_type(
        self,
        value,
    ):
        """
        Validate order type.
        """

        valid_types = [

            "dinein",

            "pickup",

            "delivery",

        ]

        if value not in valid_types:

            raise serializers.ValidationError(

                "Invalid order type."

            )

        return value

    # =========================================================================
    # Delivery Latitude
    # =========================================================================

    def validate_delivery_latitude(
        self,
        value,
    ):
        """
        Validate delivery latitude.
        """

        if value is None:

            return value

        if value < Decimal("-90"):

            raise serializers.ValidationError(

                "Latitude cannot be less than -90."

            )

        if value > Decimal("90"):

            raise serializers.ValidationError(

                "Latitude cannot exceed 90."

            )

        return value

    # =========================================================================
    # Delivery Longitude
    # =========================================================================

    def validate_delivery_longitude(
        self,
        value,
    ):
        """
        Validate delivery longitude.
        """

        if value is None:

            return value

        if value < Decimal("-180"):

            raise serializers.ValidationError(

                "Longitude cannot be less than -180."

            )

        if value > Decimal("180"):

            raise serializers.ValidationError(

                "Longitude cannot exceed 180."

            )

        return value

    # =========================================================================
    # Customer Pincode
    # =========================================================================

    def validate_customer_pincode(
        self,
        value,
    ):
        """
        Validate customer pincode.
        """

        if not value:

            return value

        value = value.strip()

        if not value.isdigit():

            raise serializers.ValidationError(

                "Pincode must contain only digits."

            )

        if len(value) < 4 or len(value) > 10:

            raise serializers.ValidationError(

                "Invalid customer pincode."

            )

        return value

    # =========================================================================
    # Tip Amount
    # =========================================================================

    def validate_tip_amount(
        self,
        value,
    ):
        """
        Validate tip amount.
        """

        if value < Decimal("0.00"):

            raise serializers.ValidationError(

                "Tip amount cannot be negative."

            )

        return value

    # =========================================================================
    # Delivery Charge
    # =========================================================================

    def validate_delivery_charge(
        self,
        value,
    ):
        """
        Validate delivery charge.
        """

        if value < Decimal("0.00"):

            raise serializers.ValidationError(

                "Delivery charge cannot be negative."

            )

        return value

    # =========================================================================
    # Subtotal
    # =========================================================================

    def validate_subtotal(
        self,
        value,
    ):
        """
        Validate subtotal.
        """

        if value < Decimal("0.00"):

            raise serializers.ValidationError(

                "Subtotal cannot be negative."

            )

        return value

    # =========================================================================
    # Grand Total
    # =========================================================================

    def validate_grand_total(
        self,
        value,
    ):
        """
        Validate grand total.
        """

        if value < Decimal("0.00"):

            raise serializers.ValidationError(

                "Grand total cannot be negative."

            )

        return value

    # =========================================================================
    # Customer Country Code
    # =========================================================================

    def validate_customer_country_code(
        self,
        value,
    ):
        """
        Validate customer phone country code.

        Examples

            +91

            +1

            +44
        """

        if not value:

            return value

        value = value.strip()

        if not value.startswith("+"):

            raise serializers.ValidationError(

                "Country code must begin with '+'."

            )

        digits = value[1:]

        if not digits.isdigit():

            raise serializers.ValidationError(

                "Country code must contain only digits."

            )

        if len(digits) < 1 or len(digits) > 4:

            raise serializers.ValidationError(

                "Invalid country code."

            )

        return value

    # =========================================================================
    # Scheduled Time
    # =========================================================================

    def validate_scheduled_time(
        self,
        value,
    ):
        """
        Validate scheduled order time.

        Rules

            • Cannot be in the past.

            • Maximum 30 days ahead.

            • Null is allowed for immediate orders.
        """

        if value is None:

            return value

        now = timezone.now()

        if value < now:

            raise serializers.ValidationError(

                "Scheduled time cannot be in the past."

            )

        maximum_date = now + timedelta(days=30)

        if value > maximum_date:

            raise serializers.ValidationError(

                "Orders can only be scheduled up to 30 days in advance."

            )

        return value
    
# =============================================================================
# Restaurant Delivery Serializer
# =============================================================================

class RestaurantDeliverySerializer(serializers.ModelSerializer):
    """
    Serializer used for managing restaurant delivery settings.

    Used By

        • GET /restaurant/delivery-settings/

        • PUT /restaurant/delivery-settings/

    Responsibilities

        • Delivery configuration

        • Pickup configuration

        • Delivery charges

        • Delivery radius

        • Preparation time
    """

    class Meta:

        model = Restaurant

        fields = [

            # ==========================================================
            # Delivery
            # ==========================================================

            "delivery_enabled",

            "pickup_enabled",

            "cash_on_delivery",

            "cash_on_pickup",

            # ==========================================================
            # Radius
            # ==========================================================

            "free_delivery_radius_km",

            "maximum_delivery_radius_km",

            # ==========================================================
            # Charges
            # ==========================================================

            "delivery_charge_per_km",

            "minimum_delivery_order",

            # ==========================================================
            # Preparation
            # ==========================================================

            "average_preparation_time",

        ]

    # ==============================================================
    # Free Delivery Radius
    # ==============================================================

    def validate_free_delivery_radius_km(
        self,
        value,
    ):

        if value < Decimal("0"):

            raise serializers.ValidationError(

                "Free delivery radius cannot be negative."

            )

        return value

    # ==============================================================
    # Maximum Radius
    # ==============================================================

    def validate_maximum_delivery_radius_km(
        self,
        value,
    ):

        if value <= Decimal("0"):

            raise serializers.ValidationError(

                "Maximum delivery radius must be greater than zero."

            )

        return value

    # ==============================================================
    # Delivery Charge
    # ==============================================================

    def validate_delivery_charge_per_km(
        self,
        value,
    ):

        if value < Decimal("0"):

            raise serializers.ValidationError(

                "Delivery charge cannot be negative."

            )

        return value

    # ==============================================================
    # Minimum Order
    # ==============================================================

    def validate_minimum_delivery_order(
        self,
        value,
    ):

        if value < Decimal("0"):

            raise serializers.ValidationError(

                "Minimum delivery order cannot be negative."

            )

        return value

    # ==============================================================
    # Preparation Time
    # ==============================================================

    def validate_average_preparation_time(
        self,
        value,
    ):

        if value <= 0:

            raise serializers.ValidationError(

                "Preparation time must be greater than zero."

            )

        return value

    # ==============================================================
    # Object Validation
    # ==============================================================

    def validate(
        self,
        attrs,
    ):

        free_radius = attrs.get(

            "free_delivery_radius_km",

            getattr(

                self.instance,

                "free_delivery_radius_km",

                Decimal("0.00"),

            )

            if self.instance else Decimal("0.00"),

        )

        maximum_radius = attrs.get(

            "maximum_delivery_radius_km",

            getattr(

                self.instance,

                "maximum_delivery_radius_km",

                Decimal("0.00"),

            )

            if self.instance else Decimal("0.00"),

        )

        if free_radius > maximum_radius:

            raise serializers.ValidationError(

                {

                    "free_delivery_radius_km":

                        "Free delivery radius cannot exceed maximum delivery radius."

                }

            )

        return attrs
    
    
    # =========================================================================
    # Object Validation
    # =========================================================================

    def validate(
        self,
        attrs,
    ):
        """
        Enterprise cross-field validation.

        Performs

            • Order Type validation

            • Delivery validation

            • Delivery location validation

            • Customer validation

            • Table validation

            • Restaurant consistency validation
        """

        # ==============================================================
        # Existing Values (PATCH Support)
        # ==============================================================

        instance = self.instance

        restaurant = attrs.get(

            "restaurant",

            getattr(
                instance,
                "restaurant",
                None,
            ) if instance else None,

        )

        table = attrs.get(

            "table",

            getattr(
                instance,
                "table",
                None,
            ) if instance else None,

        )

        order_type = attrs.get(

            "order_type",

            getattr(
                instance,
                "order_type",
                "dinein",
            ) if instance else "dinein",

        )

        latitude = attrs.get(

            "delivery_latitude",

            getattr(
                instance,
                "delivery_latitude",
                None,
            ) if instance else None,

        )

        longitude = attrs.get(

            "delivery_longitude",

            getattr(
                instance,
                "delivery_longitude",
                None,
            ) if instance else None,

        )

        customer_address = attrs.get(

            "customer_address",

            getattr(
                instance,
                "customer_address",
                "",
            ) if instance else "",

        )

        customer_city = attrs.get(

            "customer_city",

            getattr(
                instance,
                "customer_city",
                "",
            ) if instance else "",

        )

        customer_state = attrs.get(

            "customer_state",

            getattr(
                instance,
                "customer_state",
                "",
            ) if instance else "",

        )

        customer_pincode = attrs.get(

            "customer_pincode",

            getattr(
                instance,
                "customer_pincode",
                "",
            ) if instance else "",

        )

        # ==============================================================
        # Table Validation
        # ==============================================================

        if table and restaurant:

            if table.restaurant_id != restaurant.id:

                raise serializers.ValidationError(

                    {

                        "table":

                            "Selected table does not belong to the restaurant."

                    }

                )

        # ==============================================================
        # Order Type Validation
        # ==============================================================

        if order_type not in (

            "dinein",

            "pickup",

            "delivery",

        ):

            raise serializers.ValidationError(

                {

                    "order_type":

                        "Invalid order type."

                }

            )

        # ==============================================================
        # Delivery Order Validation
        # ==============================================================

        if order_type == "delivery":

            required_fields = {

                "customer_address": customer_address,

                "customer_city": customer_city,

                "customer_state": customer_state,

                "customer_pincode": customer_pincode,

            }

            for field, value in required_fields.items():

                if not value:

                    raise serializers.ValidationError(

                        {

                            field:

                                "This field is required for delivery orders."

                        }

                    )

            if latitude is None:

                raise serializers.ValidationError(

                    {

                        "delivery_latitude":

                            "Delivery latitude is required."

                    }

                )

            if longitude is None:

                raise serializers.ValidationError(

                    {

                        "delivery_longitude":

                            "Delivery longitude is required."

                    }

                )

        # ==============================================================
        # Pickup Validation
        # ==============================================================

        elif order_type == "pickup":

            if latitude is not None:

                raise serializers.ValidationError(

                    {

                        "delivery_latitude":

                            "Pickup orders should not include delivery coordinates."

                    }

                )

            if longitude is not None:

                raise serializers.ValidationError(

                    {

                        "delivery_longitude":

                            "Pickup orders should not include delivery coordinates."

                    }

                )

        # ==============================================================
        # Dine-In Validation
        # ==============================================================

        elif order_type == "dinein":

            if table is None:

                raise serializers.ValidationError(

                    {

                        "table":

                            "Table is required for dine-in orders."

                    }

                )

            if latitude is not None:

                raise serializers.ValidationError(

                    {

                        "delivery_latitude":

                            "Dine-in orders cannot have delivery coordinates."

                    }

                )

            if longitude is not None:

                raise serializers.ValidationError(

                    {

                        "delivery_longitude":

                            "Dine-in orders cannot have delivery coordinates."

                    }

                )

        # ==============================================================
        # Delivery Location Validation
        # ==============================================================

        if (

            latitude is not None

            and

            longitude is None

        ):

            raise serializers.ValidationError(

                {

                    "delivery_longitude":

                        "Longitude is required when latitude is provided."

                }

            )

        if (

            longitude is not None

            and

            latitude is None

        ):

            raise serializers.ValidationError(

                {

                    "delivery_latitude":

                        "Latitude is required when longitude is provided."

                }

            )

        # ==============================================================
        # Customer Name Required
        # ==============================================================

        customer_name = attrs.get(

            "customer_name",

            getattr(
                instance,
                "customer_name",
                "",
            ) if instance else "",

        )

        if not customer_name:

            raise serializers.ValidationError(

                {

                    "customer_name":

                        "Customer name is required."

                }

            )

        return attrs
    
    

    # =========================================================================
    # Create Order
    # =========================================================================

    @transaction.atomic
    def create(
        self,
        validated_data,
    ):
        """
        Create a new order.

        Steps

            1. Extract nested items

            2. Determine restaurant

            3. Validate table

            4. Prepare customer data

            5. Prepare delivery data

            6. Create Order

            7. Continue with item creation
               (Part 4C2)
        """

        # ==============================================================
        # Nested Items
        # ==============================================================

        items_data = validated_data.pop(

            "items",

            [],

        )

        # ==============================================================
        # Restaurant
        # ==============================================================

        restaurant = validated_data.get(
            "restaurant"
        )

        table = validated_data.get(
            "table"
        )

        # Restaurant can also be inferred from table

        if restaurant is None and table is not None:

            restaurant = table.restaurant

            validated_data["restaurant"] = restaurant

        if restaurant is None:

            raise serializers.ValidationError(

                {

                    "restaurant":

                        "Restaurant is required."

                }

            )

        # ==============================================================
        # Table Validation
        # ==============================================================

        order_type = validated_data.get(
            "order_type",
            "dinein",
        )

        if order_type == "dinein":

            if table is None:

                raise serializers.ValidationError(

                    {

                        "table":

                            "Table is required for dine-in orders."

                    }

                )

            if table.restaurant != restaurant:

                raise serializers.ValidationError(

                    {

                        "table":

                            "Selected table does not belong to this restaurant."

                    }

                )

        # ==============================================================
        # Customer Information
        # ==============================================================

        customer_name = validated_data.get(

            "customer_name",

            "",

        )

        customer_phone = validated_data.get(

            "customer_phone",

            "",

        )

        customer_email = validated_data.get(

            "customer_email",

            "",

        )

        customer_note = validated_data.get(

            "customer_note",

            "",

        )

        # ==============================================================
        # Delivery Information
        # ==============================================================

        customer_address = validated_data.get(

            "customer_address",

            "",

        )

        customer_city = validated_data.get(

            "customer_city",

            "",

        )

        customer_state = validated_data.get(

            "customer_state",

            "",

        )

        customer_pincode = validated_data.get(

            "customer_pincode",

            "",

        )

        delivery_latitude = validated_data.get(

            "delivery_latitude",

        )

        delivery_longitude = validated_data.get(

            "delivery_longitude",

        )

        # ==============================================================
        # Status Initialization
        # ==============================================================

        validated_data.setdefault(

            "status",

            "pending",

        )

        validated_data.setdefault(

            "payment_status",

            "pending",

        )

        validated_data.setdefault(

            "is_completed",

            False,

        )

        validated_data.setdefault(

            "pickup_verified",

            False,

        )

        validated_data.setdefault(

            "delivery_verified",

            False,

        )

        validated_data.setdefault(

            "kitchen_printed",

            False,

        )

        validated_data.setdefault(

            "receipt_printed",

            False,

        )

        validated_data.setdefault(

            "is_deleted",

            False,

        )

        # ==============================================================
        # Create Order
        # ==============================================================

        order = Order.objects.create(

            restaurant=restaurant,

            table=table,

            customer_name=customer_name,

            customer_phone=customer_phone,

            customer_email=customer_email,

            customer_note=customer_note,

            customer_country=validated_data.get(
                "customer_country"
            ),

            customer_country_code=validated_data.get(
                "customer_country_code"
            ),

            customer_address=customer_address,

            customer_city=customer_city,

            customer_state=customer_state,

            customer_pincode=customer_pincode,

            order_type=order_type,

            delivery_latitude=delivery_latitude,

            delivery_longitude=delivery_longitude,

            scheduled_time=validated_data.get(
                "scheduled_time"
            ),

            status=validated_data["status"],

            payment_status=validated_data["payment_status"],

            is_completed=validated_data["is_completed"],

            pickup_verified=validated_data["pickup_verified"],

            delivery_verified=validated_data["delivery_verified"],

            kitchen_printed=validated_data["kitchen_printed"],

            receipt_printed=validated_data["receipt_printed"],

            is_deleted=validated_data["is_deleted"],

            tip_amount=validated_data.get(
                "tip_amount",
                Decimal("0.00"),
            ),

        )

        # ==============================================================
        # Continue in Part 4C2
        # ==============================================================
        # Running Subtotal
        # ==============================================================

        subtotal = Decimal("0.00")

        # ==============================================================
        # Create Order Items
        # ==============================================================

        for item_data in items_data:

            # ----------------------------------------------------------
            # Food Item
            # ----------------------------------------------------------

            food_item_id = item_data.get(
                "food_item_id"
            )

            if not food_item_id:

                raise serializers.ValidationError(

                    {
                        "food_item_id":
                            "Food item is required."
                    }

                )

            try:

                food_item = FoodItem.objects.select_related(

                    "restaurant"

                ).get(

                    id=food_item_id

                )

            except FoodItem.DoesNotExist:

                raise serializers.ValidationError(

                    {
                        "food_item_id":
                            "Food item not found."
                    }

                )

            # ----------------------------------------------------------
            # Restaurant Validation
            # ----------------------------------------------------------

            if food_item.restaurant_id != restaurant.id:

                raise serializers.ValidationError(

                    {
                        "food_item_id":
                            (
                                f"{food_item.name} "
                                "does not belong to this restaurant."
                            )
                    }

                )

            # ----------------------------------------------------------
            # Availability
            # ----------------------------------------------------------

            if food_item.is_paused:

                raise serializers.ValidationError(

                    {
                        "food_item_id":
                            (
                                f"{food_item.name} "
                                "is currently unavailable."
                            )
                    }

                )

            # ----------------------------------------------------------
            # Quantity
            # ----------------------------------------------------------

            quantity = item_data.get(

                "quantity",

                1,

            )

            if quantity <= 0:

                raise serializers.ValidationError(

                    {
                        "quantity":
                            (
                                "Quantity must be greater than zero."
                            )
                    }

                )

            if quantity > 100:

                raise serializers.ValidationError(

                    {
                        "quantity":
                            (
                                "Maximum quantity is 100."
                            )
                    }

                )

            # ----------------------------------------------------------
            # Create Order Item
            # ----------------------------------------------------------

            order_item = OrderItem.objects.create(

                order=order,

                food_item=food_item,

                quantity=quantity,

            )

            # ----------------------------------------------------------
            # Continue in Part 4C2B
            # ----------------------------------------------------------
            # Selected Addons
            # ----------------------------------------------------------

            addon_ids = item_data.get(

                "selected_addons_ids",

                [],

            )

            selected_addons = []

            # ----------------------------------------------------------
            # Addon Lookup
            # ----------------------------------------------------------

            if addon_ids:

                selected_addons = list(

                    AddOn.objects.filter(

                        id__in=addon_ids

                    )

                )

                # ------------------------------------------------------
                # Missing Addons
                # ------------------------------------------------------

                if len(selected_addons) != len(addon_ids):

                    raise serializers.ValidationError(

                        {

                            "selected_addons_ids":

                                "One or more selected addons do not exist."

                        }

                    )

            # ----------------------------------------------------------
            # Addon Validation
            # ----------------------------------------------------------

            food_item_addons = set(

                food_item.addons.values_list(

                    "id",

                    flat=True,

                )

            )

            for addon in selected_addons:

                if addon.id not in food_item_addons:

                    raise serializers.ValidationError(

                        {

                            "selected_addons_ids":

                                (

                                    f"{addon.name} "

                                    "is not available for "

                                    f"{food_item.name}."

                                )

                        }

                    )

            # ----------------------------------------------------------
            # Assign Addons
            # ----------------------------------------------------------

            if selected_addons:

                order_item.selected_addons.set(

                    selected_addons

                )

            # ----------------------------------------------------------
            # Base Price
            # ----------------------------------------------------------

            base_price = (

                food_item.price

                or Decimal("0.00")

            )

            base_total = (

                base_price

                * quantity

            )

            # ----------------------------------------------------------
            # Addon Price
            # ----------------------------------------------------------

            addon_total = Decimal("0.00")

            for addon in selected_addons:

                addon_total += (

                    addon.price

                    or Decimal("0.00")

                )

            addon_total *= quantity

            # ----------------------------------------------------------
            # Line Total
            # ----------------------------------------------------------

            line_total = (

                base_total

                + addon_total

            )

            # ----------------------------------------------------------
            # Running Subtotal
            # ----------------------------------------------------------

            subtotal += line_total
            
            
            # ==============================================================
            # Calculate Order Totals
            # ==============================================================

            update_order_totals(order)

            # ==============================================================
            # Tip
            # ==============================================================

            order.tip_amount = validated_data.get(

                "tip_amount",

                Decimal("0.00"),

            )

            if order.tip_amount:

                order.grand_total += order.tip_amount

                order.total_price_cached = order.grand_total

                order.save(

                    update_fields=[

                        "tip_amount",

                        "grand_total",

                        "total_price_cached",

                    ]

                )

            # ==============================================================
            # Return
            # ==============================================================

            return order
        
        
        
    # =========================================================================
    # Update Order
    # =========================================================================

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):
        """
        Update an existing order.

        Responsibilities

            • Update editable fields

            • Synchronize order status

            • Synchronize completion flags

            • Update delivery information

            • Recalculate totals

            • Persist changes

        Returns
        -------
        Order
        """

        # ==============================================================
        # Nested Items
        # ==============================================================
        #
        # Order items are managed through dedicated APIs.
        # Ignore nested item updates here.
        #
        # ==============================================================

        validated_data.pop(
            "items",
            None,
        )

        # ==============================================================
        # Status
        # ==============================================================

        status_value = validated_data.get(

            "status",

            instance.status,

        )

        instance.status = status_value

        # ==============================================================
        # Status Synchronization
        # ==============================================================

        if status_value == "completed":

            instance.is_completed = True

            if instance.completed_at is None:

                instance.completed_at = timezone.now()

        else:

            instance.is_completed = False

            if status_value != "completed":

                instance.completed_at = None

        # ==============================================================
        # Payment Synchronization
        # ==============================================================

        payment_status = validated_data.get(

            "payment_status",

            instance.payment_status,

        )

        instance.payment_status = payment_status

        # ==============================================================
        # Customer Information
        # ==============================================================

        customer_fields = [

            "customer_name",

            "customer_phone",

            "customer_email",

            "customer_country",

            "customer_country_code",

            "customer_note",

        ]

        for field in customer_fields:

            if field in validated_data:

                setattr(

                    instance,

                    field,

                    validated_data[field],

                )

        # ==============================================================
        # Delivery Address
        # ==============================================================

        delivery_fields = [

            "customer_address",

            "customer_city",

            "customer_state",

            "customer_pincode",

            "delivery_latitude",

            "delivery_longitude",

            "scheduled_time",

        ]

        for field in delivery_fields:

            if field in validated_data:

                setattr(

                    instance,

                    field,

                    validated_data[field],

                )

        # ==============================================================
        # Delivery Assignment
        # ==============================================================

        assignment_fields = [

            "delivery_person_name",

            "delivery_person_phone",

            "assigned_at",

            "picked_at",

            "delivered_at",

            "delivery_status",

        ]

        for field in assignment_fields:

            if field in validated_data:

                setattr(

                    instance,

                    field,

                    validated_data[field],

                )

        # ==============================================================
        # Verification Flags
        # ==============================================================

        verification_fields = [

            "pickup_verified",

            "delivery_verified",

            "kitchen_printed",

            "receipt_printed",

            "is_deleted",

        ]

        for field in verification_fields:

            if field in validated_data:

                setattr(

                    instance,

                    field,

                    validated_data[field],

                )

        # ==============================================================
        # Tip
        # ==============================================================

        if "tip_amount" in validated_data:

            instance.tip_amount = validated_data[
                "tip_amount"
            ]

        # ==============================================================
        # Recalculate Totals
        # ==============================================================

        update_order_totals(
            instance
        )

        # ==============================================================
        # Save Order
        # ==============================================================

        instance.save()

        instance.refresh_from_db()

        # ==============================================================
        # Return
        # ==============================================================

        return instance

# =============================================================================
# Restaurant Location Serializer
# =============================================================================

class RestaurantLocationSerializer(serializers.ModelSerializer):
    """
    Serializer used for updating the restaurant's map location.

    Used By

        PATCH /restaurant/location/

    Responsibilities

        • Restaurant map location

        • Delivery origin

        • Coordinate validation
    """

    class Meta:

        model = Restaurant

        fields = [

            "delivery_latitude",

            "delivery_longitude",

        ]

    # ==============================================================
    # Latitude
    # ==============================================================

    def validate_delivery_latitude(
        self,
        value,
    ):

        if value is None:

            raise serializers.ValidationError(

                "Latitude is required."

            )

        if value < Decimal("-90"):

            raise serializers.ValidationError(

                "Latitude cannot be less than -90."

            )

        if value > Decimal("90"):

            raise serializers.ValidationError(

                "Latitude cannot exceed 90."

            )

        return value

    # ==============================================================
    # Longitude
    # ==============================================================

    def validate_delivery_longitude(
        self,
        value,
    ):

        if value is None:

            raise serializers.ValidationError(

                "Longitude is required."

            )

        if value < Decimal("-180"):

            raise serializers.ValidationError(

                "Longitude cannot be less than -180."

            )

        if value > Decimal("180"):

            raise serializers.ValidationError(

                "Longitude cannot exceed 180."

            )

        return value

    # ==============================================================
    # Object Validation
    # ==============================================================

    def validate(
        self,
        attrs,
    ):

        latitude = attrs.get(

            "delivery_latitude",

            getattr(

                self.instance,

                "delivery_latitude",

                None,

            )

            if self.instance else None,

        )

        longitude = attrs.get(

            "delivery_longitude",

            getattr(

                self.instance,

                "delivery_longitude",

                None,

            )

            if self.instance else None,

        )

        if latitude is None:

            raise serializers.ValidationError(

                {

                    "delivery_latitude":

                        "Restaurant latitude is required."

                }

            )

        if longitude is None:

            raise serializers.ValidationError(

                {

                    "delivery_longitude":

                        "Restaurant longitude is required."

                }

            )

        return attrs
    
    
# =============================================================================
# Nearby Restaurant Serializer
# =============================================================================

class NearbyRestaurantSerializer(serializers.ModelSerializer):
    """
    Serializer used by the customer application
    to display nearby restaurants.
    """

    logo_url = serializers.SerializerMethodField()

    cover_image_url = serializers.SerializerMethodField()

    distance_km = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        read_only=True,
    )

    class Meta:

        model = Restaurant

        fields = [

            "id",

            "name",

            "logo_url",

            "cover_image_url",

            "about",

            "address",

            "city",

            "state",

            "phone",

            "cuisine_type",

            "delivery_enabled",

            "pickup_enabled",

            "free_delivery_radius_km",

            "maximum_delivery_radius_km",

            "minimum_delivery_order",

            "delivery_charge_per_km",

            "average_preparation_time",

            "distance_km",

        ]

    # ==========================================================
    # Logo URL
    # ==========================================================

    def get_logo_url(self, obj):

        request = self.context.get("request")

        if not obj.logo:
            return None

        if request:
            return request.build_absolute_uri(
                obj.logo.url
            )

        return obj.logo.url

    # ==========================================================
    # Cover URL
    # ==========================================================

    def get_cover_image_url(self, obj):

        request = self.context.get("request")

        if not obj.cover_image:
            return None

        if request:
            return request.build_absolute_uri(
                obj.cover_image.url
            )

        return obj.cover_image.url
    
# =============================================================================
# Order Delivery Serializer
# =============================================================================

class OrderDeliverySerializer(serializers.ModelSerializer):
    """
    Serializer for updating delivery information
    after the order has been created.
    """

    class Meta:

        model = Order

        fields = [

            "customer_address",

            "customer_city",

            "customer_state",

            "customer_pincode",

            "delivery_latitude",

            "delivery_longitude",

            "delivery_distance_km",

            "delivery_charge",

            "scheduled_time",

        ]

        read_only_fields = [

            "delivery_distance_km",

            "delivery_charge",

        ]

    # ==========================================================
    # Object Validation
    # ==========================================================

    def validate(self, attrs):

        latitude = attrs.get(
            "delivery_latitude"
        )

        longitude = attrs.get(
            "delivery_longitude"
        )

        if latitude is None:

            raise serializers.ValidationError(

                {

                    "delivery_latitude":

                    "Latitude is required."

                }

            )

        if longitude is None:

            raise serializers.ValidationError(

                {

                    "delivery_longitude":

                    "Longitude is required."

                }

            )

        return attrs
    
# =============================================================================
# Delivery Validation Serializer
# =============================================================================

class DeliveryValidationSerializer(serializers.Serializer):
    """
    Validate a customer delivery request
    before an order is created.
    """

    restaurant_id = serializers.IntegerField()

    latitude = serializers.DecimalField(

        max_digits=10,

        decimal_places=7,

    )

    longitude = serializers.DecimalField(

        max_digits=10,

        decimal_places=7,

    )

    subtotal = serializers.DecimalField(

        max_digits=10,

        decimal_places=2,

    )

    # ==========================================================
    # Latitude
    # ==========================================================

    def validate_latitude(self, value):

        if value < -90 or value > 90:

            raise serializers.ValidationError(

                "Invalid latitude."

            )

        return value

    # ==========================================================
    # Longitude
    # ==========================================================

    def validate_longitude(self, value):

        if value < -180 or value > 180:

            raise serializers.ValidationError(

                "Invalid longitude."

            )

        return value

    # ==========================================================
    # Subtotal
    # ==========================================================

    def validate_subtotal(self, value):

        if value <= 0:

            raise serializers.ValidationError(

                "Subtotal must be greater than zero."

            )

        return value
    
    
# =============================================================================
# Restaurant Map Serializer
# =============================================================================

class RestaurantMapSerializer(serializers.ModelSerializer):
    """
    Serializer used by the customer application
    to display the restaurant on a map.

    Includes

        • Restaurant coordinates

        • Delivery radius

        • Basic restaurant information
    """

    logo_url = serializers.SerializerMethodField()

    class Meta:

        model = Restaurant

        fields = [

            "id",

            "name",

            "address",

            "city",

            "state",

            "country",

            "phone",

            "logo_url",

            # Map

            "delivery_latitude",

            "delivery_longitude",

            # Radius

            "free_delivery_radius_km",

            "maximum_delivery_radius_km",

            # Delivery

            "delivery_enabled",

            "pickup_enabled",

        ]

    # ==========================================================
    # Logo URL
    # ==========================================================

    def get_logo_url(self, obj):

        request = self.context.get("request")

        if not obj.logo:
            return None

        if request:

            return request.build_absolute_uri(

                obj.logo.url

            )

        return obj.logo.url
    
    
# =============================================================================
# Customer Location Serializer
# =============================================================================

class CustomerLocationSerializer(serializers.Serializer):
    """
    Serializer used when the customer
    selects a location from the map.
    """

    latitude = serializers.DecimalField(

        max_digits=10,

        decimal_places=7,

    )

    longitude = serializers.DecimalField(

        max_digits=10,

        decimal_places=7,

    )

    address = serializers.CharField(

        required=False,

        allow_blank=True,

    )

    city = serializers.CharField(

        required=False,

        allow_blank=True,

    )

    state = serializers.CharField(

        required=False,

        allow_blank=True,

    )

    pincode = serializers.CharField(

        required=False,

        allow_blank=True,

    )

    # ==========================================================
    # Latitude
    # ==========================================================

    def validate_latitude(self, value):

        if value < -90:

            raise serializers.ValidationError(

                "Latitude cannot be less than -90."

            )

        if value > 90:

            raise serializers.ValidationError(

                "Latitude cannot exceed 90."

            )

        return value

    # ==========================================================
    # Longitude
    # ==========================================================

    def validate_longitude(self, value):

        if value < -180:

            raise serializers.ValidationError(

                "Longitude cannot be less than -180."

            )

        if value > 180:

            raise serializers.ValidationError(

                "Longitude cannot exceed 180."

            )

        return value
    
    
# =============================================================================
# Delivery Quote Serializer
# =============================================================================

class DeliveryQuoteSerializer(serializers.Serializer):
    """
    Used before order creation.

    Calculates

        • Delivery availability

        • Delivery distance

        • Delivery charge

        • Estimated preparation time

        • Estimated delivery time
    """

    restaurant_id = serializers.IntegerField()

    latitude = serializers.DecimalField(

        max_digits=10,

        decimal_places=7,

    )

    longitude = serializers.DecimalField(

        max_digits=10,

        decimal_places=7,

    )

    subtotal = serializers.DecimalField(

        max_digits=10,

        decimal_places=2,

    )

    coupon_code = serializers.CharField(

        required=False,

        allow_blank=True,

    )

    # ==========================================================
    # Latitude
    # ==========================================================

    def validate_latitude(self, value):

        if value < -90 or value > 90:

            raise serializers.ValidationError(

                "Invalid latitude."

            )

        return value

    # ==========================================================
    # Longitude
    # ==========================================================

    def validate_longitude(self, value):

        if value < -180 or value > 180:

            raise serializers.ValidationError(

                "Invalid longitude."

            )

        return value

    # ==========================================================
    # Subtotal
    # ==========================================================

    def validate_subtotal(self, value):

        if value <= 0:

            raise serializers.ValidationError(

                "Subtotal must be greater than zero."

            )

        return value

    # ==========================================================
    # Object Validation
    # ==========================================================

    def validate(self, attrs):

        restaurant = Restaurant.objects.filter(

            id=attrs["restaurant_id"]

        ).first()

        if restaurant is None:

            raise serializers.ValidationError(

                {

                    "restaurant_id":

                    "Restaurant not found."

                }

            )

        if not restaurant.delivery_enabled:

            raise serializers.ValidationError(

                "Delivery is not enabled for this restaurant."

            )

        return attrs
    
    
# =============================================================================
# Delivery Assignment Serializer
# =============================================================================

class DeliveryAssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer used for assigning a delivery
    executive to an order.
    """

    class Meta:

        model = Order

        fields = [

            "delivery_person_name",

            "delivery_person_phone",

            "delivery_status",

            "assigned_at",

            "picked_at",

            "delivered_at",

        ]

        read_only_fields = [

            "assigned_at",

            "picked_at",

            "delivered_at",

        ]

    # ==========================================================
    # Delivery Person
    # ==========================================================

    def validate_delivery_person_name(self, value):

        value = value.strip()

        if len(value) < 2:

            raise serializers.ValidationError(

                "Delivery person name is too short."

            )

        return value

    # ==========================================================
    # Phone
    # ==========================================================

    def validate_delivery_person_phone(self, value):

        digits = "".join(

            c

            for c in value

            if c.isdigit()

        )

        if len(digits) < 8:

            raise serializers.ValidationError(

                "Invalid phone number."

            )

        return value

    # ==========================================================
    # Delivery Status
    # ==========================================================

    def validate_delivery_status(self, value):

        valid = [

            "pending",

            "assigned",

            "picked",

            "out_for_delivery",

            "delivered",

            "failed",

        ]

        if value not in valid:

            raise serializers.ValidationError(

                "Invalid delivery status."

            )

        return value
    
# =============================================================================
# Delivery Tracking Serializer
# =============================================================================

class DeliveryTrackingSerializer(serializers.ModelSerializer):
    """
    Serializer used by customers to
    track live delivery.
    """

    estimated_delivery_time = serializers.SerializerMethodField()

    class Meta:

        model = Order

        fields = [

            "id",

            "status",

            "delivery_status",

            "delivery_person_name",

            "delivery_person_phone",

            "assigned_at",

            "picked_at",

            "delivered_at",

            "delivery_distance_km",

            "estimated_delivery_time",

        ]

    # ==========================================================
    # ETA
    # ==========================================================

    def get_estimated_delivery_time(self, obj):

        if obj.delivered_at:

            return obj.delivered_at

        if obj.picked_at:

            return (

                obj.picked_at

                + timedelta(minutes=20)

            )

        return None
    
# =============================================================================
# Delivery Charge Breakdown Serializer
# =============================================================================

class DeliveryChargeBreakdownSerializer(serializers.Serializer):
    """
    Displays a complete delivery
    price breakdown.
    """

    distance_km = serializers.DecimalField(

        max_digits=8,

        decimal_places=2,

    )

    free_radius_km = serializers.DecimalField(

        max_digits=8,

        decimal_places=2,

    )

    charge_per_km = serializers.DecimalField(

        max_digits=8,

        decimal_places=2,

    )

    subtotal = serializers.DecimalField(

        max_digits=10,

        decimal_places=2,

    )

    delivery_charge = serializers.DecimalField(

        max_digits=10,

        decimal_places=2,

    )

    tax = serializers.DecimalField(

        max_digits=10,

        decimal_places=2,

    )

    grand_total = serializers.DecimalField(

        max_digits=10,

        decimal_places=2,

    )

    free_delivery = serializers.BooleanField()

    minimum_order_met = serializers.BooleanField()
    
    
# =============================================================================
# Restaurant Delivery Zone Serializer
# =============================================================================

class RestaurantDeliveryZoneSerializer(serializers.ModelSerializer):
    """
    Returns the delivery zone
    configuration of a restaurant.
    """

    class Meta:

        model = Restaurant

        fields = [

            "id",

            "name",

            "delivery_enabled",

            "delivery_latitude",

            "delivery_longitude",

            "free_delivery_radius_km",

            "maximum_delivery_radius_km",

            "delivery_charge_per_km",

            "minimum_delivery_order",

            "average_preparation_time",

        ]
        
        
