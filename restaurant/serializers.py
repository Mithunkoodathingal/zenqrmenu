# ----------restaurant/serializers.py---------------

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
from drf_spectacular.utils import extend_schema_field

from drf_spectacular.types import OpenApiTypes

# =============================================================================
# Django Imports
# =============================================================================

from datetime import timedelta

from django.utils import timezone

from django.db import transaction

from decimal import Decimal

from django.db.models import Count, Sum

from django.utils import timezone

    
from rest_framework import serializers

# =============================================================================
# Django REST Framework Imports
# =============================================================================

from rest_framework import serializers

from payments.services import calculate_discount, calculate_grand_total, calculate_packing_charge, calculate_subtotal, calculate_tax, update_order_totals

from restaurant.services.delivery import calculate_delivery_charge

# =============================================================================
# Local Application Imports
# =============================================================================

from .models import AuditLog, DeliveryPartner, KitchenNote, Staff, StaffAttendance, StaffBreak, StaffShiftSchedule

from .models import (
    
    Restaurant,
    
    Order,
    
    OrderItem,
    
    FoodItem,
    
    AddOn,
    
    Category,
    
)





# =============================================================================
# User Serializer
# =============================================================================

class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    
# =============================================================================
# User Response Serializer
# =============================================================================
class UserResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    user = UserSerializer()
    
# =============================================================================
# Register Serializer
# =============================================================================

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    
# =============================================================================
# Register Response Filter Serializer
# =============================================================================

class RegisterResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    email = serializers.EmailField()

# =============================================================================
#  Login Serializer
# =============================================================================

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        help_text="Username or email address"
    )
    password = serializers.CharField(write_only=True)
    
# =============================================================================
#  Google - Login Serializer
# =============================================================================

class GoogleLoginSerializer(serializers.Serializer):
    token = serializers.CharField()

# =============================================================================
# Login Response Serializer
# =============================================================================

class LoginResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

# =============================================================================
# Logout Response Serializer
# =============================================================================

class LogoutResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    
# =============================================================================
# Error Serializer
# =============================================================================

class ErrorSerializer(serializers.Serializer):
    """Generic error response serializer."""
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    error_code = serializers.CharField(required=False)

# =============================================================================
# Validation Error Serializer
# =============================================================================

class ValidationErrorSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    errors = serializers.DictField(
        child=serializers.ListField(
            child=serializers.CharField() ))
    
# =============================================================================
# Authentication Error Serializer
# =============================================================================
    
class AuthenticationErrorSerializer(serializers.Serializer):
    error = serializers.CharField()
    
# =============================================================================
# Email Serializer
# =============================================================================

class EmailSerializer(serializers.Serializer):
    """Serializer for email input."""
    email = serializers.EmailField(required=True)
    
# =============================================================================
# Email - Verification Required Serializer
# =============================================================================
    
class EmailVerificationRequiredSerializer(serializers.Serializer):
    error = serializers.CharField()
    email = serializers.EmailField()
    
# =============================================================================
# Password - Reset Serializer
# =============================================================================

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password1 = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

# =============================================================================
# Success Serializer
# =============================================================================
class SuccessSerializer(serializers.Serializer):
    """Serializer for success responses."""
    message = serializers.CharField()
    success = serializers.BooleanField(default=True)
    

    
    
    
    
    

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






# =============================================================================
# Restaurant Serializer
# =============================================================================

class RestaurantSerializer(serializers.ModelSerializer):
    """
    Enterprise serializer for Restaurant.
    
    POST /restaurants/, PUT/PATCH /restaurants/{id}/

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
    def validate_name(self, value: str) -> str:
    # def validate_name(self, value):
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

    @extend_schema_field(OpenApiTypes.URI)
    def get_logo_url(self, obj) -> str | None:
    # def get_logo_url(self, obj):
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
        instance: Restaurant,
        validated_data: dict,
    ) -> Restaurant:
    # def update(
    #     self,
    #     instance,
    #     validated_data,
    # ):
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

# =============================================================================
# Restaurant Category Serializer
# =============================================================================

class RestaurantCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
        ]






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
    def validate_name(self, value: str) -> str:
    # def validate_name(self, value):
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
        instance: FoodItem,
        validated_data: dict,
    ) -> FoodItem:
        
        
    # def update(
    #     self,
    #     instance,
    #     validated_data,
    # ):
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
        instance: OrderItem,
        validated_data: dict,
    ) -> OrderItem:
        
    # def update(
    #     self,
    #     instance,
    #     validated_data,
    # ):

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

# =============================================================================
# Public Table Order Serialize
# =============================================================================

class PublicTableOrderSerializer(serializers.ModelSerializer):
    order_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "total_price_cached",
            "created_at",
            "order_items",
        ]

    def get_order_items(self, obj):
        return [
            {
                "id": item.id,
                "food_item_id": item.food_item_id,
                "food_item_name": item.food_item.name,
                "quantity": item.quantity,
            }
            for item in obj.order_items.select_related("food_item").all()
        ]


# =================== CATEGORY SERIALIZER ============== 

# class CategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Category
#         fields = ["id", "name"]

# ======================================================



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


# =============================================================================
# Restaurant List Serializer
# =============================================================================

class RestaurantListSerializer(RestaurantSerializer):
    """
    Lightweight serializer used for restaurant listing.

    Used By

        • Restaurant List API
        
        GET /restaurants/

    Purpose

        • Reduce response payload
        • Improve API performance
        • Customer restaurant browsing
    """

    class Meta(RestaurantSerializer.Meta):

        fields = [

            "id",

            "name",

            "about",

            "city",

            "state",

            "country",

            "cuisine_type",

            "logo_url",

            "cover_image_url",

            "delivery_enabled",

            "pickup_enabled",

            "average_preparation_time",

        ]

        read_only_fields = fields

# =============================================================================
# Nearby Restaurant Serializer
# =============================================================================

class NearbyRestaurantSerializer(RestaurantListSerializer):
    """
    Serializer used by the Nearby Restaurants API.
    
    GET /restaurants/nearby/

    Includes calculated distance from the customer.
    """

    distance_km = serializers.SerializerMethodField()

    class Meta(RestaurantListSerializer.Meta):

        fields = RestaurantListSerializer.Meta.fields + [

            "distance_km",

        ]

        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distance_km(self, obj) -> float | None:

        distance = getattr(obj, "distance_km", None)

        if distance is None:
            return None

        return round(float(distance), 2)
        
# =============================================================================
# Nearby Restaurant Request Serializer
# =============================================================================

class NearbyRestaurantRequestSerializer(serializers.Serializer):
    """
    Request serializer for nearby restaurants.
    """

    latitude = serializers.FloatField(

        min_value=-90,

        max_value=90,

    )

    longitude = serializers.FloatField(

        min_value=-180,

        max_value=180,

    )        

# =============================================================================
# Restaurant List Request Serializer
# =============================================================================

class RestaurantListRequestSerializer(serializers.Serializer):
    """
    Query parameters for restaurant discovery.
    """

    search = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    city = serializers.CharField(
        required=False,
    )

    state = serializers.CharField(
        required=False,
    )

    country = serializers.CharField(
        required=False,
    )

    cuisine = serializers.CharField(
        required=False,
    )

    delivery = serializers.BooleanField(
        required=False,
    )

    pickup = serializers.BooleanField(
        required=False,
    )

    dine_in = serializers.BooleanField(
        required=False,
    )

    ordering = serializers.ChoiceField(
        choices=[
            "name",
            "-name",
            "created_at",
            "-created_at",
        ],
        required=False,
        default="name",
    )

    latitude = serializers.FloatField(
        required=False,
    )

    longitude = serializers.FloatField(
        required=False,
    )

# =============================================================================
# Restaurant Detail Serializer
# =============================================================================

class RestaurantDetailSerializer(RestaurantSerializer):
    """
    Detailed serializer for a single restaurant.

    Used By

        • Restaurant Details API
        
        GET /restaurants/{id}/

    Includes nested relationships.
    """

    categories = RestaurantCategorySerializer(
        many=True,
        read_only=True,
    )

    class Meta(RestaurantSerializer.Meta):

        fields = RestaurantSerializer.Meta.fields + [

            "categories",

        ]

        read_only_fields = [

            "id",
            "owner",
            "logo_url",
            "cover_image_url",
            "categories",

        ]
        

# =============================================================================
# Restaurant Create Request Serializer
# =============================================================================

class RestaurantCreateRequestSerializer(RestaurantSerializer):
    """
    Request serializer for creating a restaurant.

    Used By

        • Create Restaurant API

    Notes

        • Owner is assigned automatically.
        • Computed fields are read-only.
    """

    class Meta(RestaurantSerializer.Meta):

        fields = [

            # ==========================================================
            # Basic Information
            # ==========================================================

            "name",

            "about",

            "address",

            "city",

            "state",

            "country",

            "pincode",

            "cuisine_type",

            # ==========================================================
            # Images
            # ==========================================================

            "logo",

            "cover_image",

            # ==========================================================
            # Contact
            # ==========================================================

            "phone_country_code",

            "phone",

            "alternate_phone",

            "email",

            "website",

            # ==========================================================
            # Tax
            # ==========================================================

            "tax_enabled",

            "tax_name",

            "tax_percentage",

            "prices_include_tax",

            "tax_registration_number",

            "fssai_number",

            "cgst_percentage",

            "sgst_percentage",

            "igst_percentage",

            # ==========================================================
            # Invoice
            # ==========================================================

            "invoice_prefix",

            "currency_code",

            "currency_symbol",

            "currency_decimal_places",

            "footer_message",

            "timezone",

            # ==========================================================
            # Payments
            # ==========================================================

            "default_payment_gateway",

            # ==========================================================
            # Delivery
            # ==========================================================

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
        
# =============================================================================
# Restaurant Update Request Serializer
# =============================================================================

class RestaurantUpdateRequestSerializer(RestaurantSerializer):
    """
    Request serializer for updating a restaurant.

    Used By

        • Update Restaurant API

    Notes

        • Owner cannot be changed.
        • ID cannot be changed.
        • Computed fields remain read-only.
    """

    class Meta(RestaurantSerializer.Meta):

        fields = RestaurantCreateRequestSerializer.Meta.fields
        
                
# =============================================================================
# Restaurant Response Serializer
# =============================================================================

class RestaurantResponseSerializer(serializers.Serializer):
    """
    Standard response returned after successful
    restaurant create, retrieve and update operations.
    """

    success = serializers.BooleanField()

    message = serializers.CharField()

    restaurant = RestaurantSerializer(read_only=True)
    
    
# =============================================================================
# Restaurant List Response Serializer
# =============================================================================

class RestaurantListResponseSerializer(serializers.Serializer):
    """
    Response serializer for restaurant listing.
    """

    success = serializers.BooleanField(
        default=True
    )

    count = serializers.IntegerField()

    restaurants = RestaurantListSerializer(
        many=True
    )
    
    
# =============================================================================
# Nearby Restaurant Response Serializer
# =============================================================================

class NearbyRestaurantResponseSerializer(serializers.Serializer):
    """
    Response serializer for nearby restaurants.
    """

    success = serializers.BooleanField(
        default=True
    )

    count = serializers.IntegerField()

    restaurants = NearbyRestaurantSerializer(
        many=True
    )
    
# =============================================================================
# Restaurant Detail Response Serializer
# =============================================================================

class RestaurantDetailResponseSerializer(serializers.Serializer):
    """
    Response serializer for restaurant details.
    """

    success = serializers.BooleanField(
        default=True
    )

    restaurant = RestaurantDetailSerializer()
    
# =============================================================================
# Restaurant Delete Response Serializer
# =============================================================================

class RestaurantDeleteResponseSerializer(serializers.Serializer):
    """
    Response serializer returned after deleting a restaurant.
    """

    success = serializers.BooleanField(
        default=True
    )

    message = serializers.CharField()
    
    
# =============================================================================
# My Restaurant Response Serializer
# =============================================================================

class MyRestaurantResponseSerializer(serializers.Serializer):
    """
    Response serializer for the authenticated user's restaurant.
    """

    success = serializers.BooleanField(
        default=True,
    )

    restaurant = RestaurantDetailSerializer()


# =============================================================================
# Update Restaurant Response Serializer
# =============================================================================

class UpdateRestaurantResponseSerializer(serializers.Serializer):
    """
    Response serializer returned after successfully updating
    a restaurant.
    """

    success = serializers.BooleanField(
        default=True,
    )

    message = serializers.CharField()

    restaurant = RestaurantDetailSerializer()


# =============================================================================
# Restaurant Not Found Serializer
# =============================================================================

class RestaurantNotFoundSerializer(serializers.Serializer):
    """
    Response serializer when a restaurant cannot be found.
    """

    success = serializers.BooleanField(
        default=False,
    )

    message = serializers.CharField(
        default="Restaurant not found.",
    )


# =============================================================================
# Restaurant Permission Denied Serializer
# =============================================================================

class RestaurantPermissionDeniedSerializer(serializers.Serializer):
    """
    Response serializer when the authenticated user does not
    have permission to access or modify a restaurant.
    """

    success = serializers.BooleanField(
        default=False,
    )

    message = serializers.CharField(
        default="You do not have permission to perform this action.",
    )












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
    
    delivery_person_name = serializers.SerializerMethodField()

    delivery_person_phone = serializers.SerializerMethodField()
    
    # ============================================================
    # Delivery Partner
    # ============================================================

    def get_delivery_person_name(self, obj) -> str | None:

        if not obj.delivery_partner:
            return None

        return (
            f"{obj.delivery_partner.first_name} "
            f"{obj.delivery_partner.last_name}"
        ).strip()


    def get_delivery_person_phone(self, obj) -> str | None:

        if not obj.delivery_partner:
            return None

        return obj.delivery_partner.mobile

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

            # ===========================================================
            # Items
            # ===========================================================

            "items": {

                "required": True,

            },

        }
        
        
    # =========================================================================
    #   Create Item Function
    # =========================================================================

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items", [])

        if not items_data:
            raise serializers.ValidationError({
                "items": "At least one order item is required."
            })

        # Create the parent order without passing nested items to the model.
        order = Order.objects.create(**validated_data)

        # Create each item and associate it with this order.
        for item_data in items_data:
            addon_ids = item_data.pop("selected_addons_ids", [])
            food_item_id = item_data.pop("food_item_id")

            food_item = FoodItem.objects.get(id=food_item_id)

            order_item = OrderItem.objects.create(
                order=order,
                food_item=food_item,
                **item_data,
            )

            if addon_ids:
                order_item.selected_addons.set(
                    AddOn.objects.filter(id__in=addon_ids)
                )

        return order

        
        
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
    def update(
        self,
        instance: Restaurant,
        validated_data: dict,
    ) -> Restaurant:

    # @transaction.atomic
    # def update(
    #     self,
    #     instance,
    #     validated_data,
    # ):
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
    
    @extend_schema_field(OpenApiTypes.URI)
    def get_logo_url(self, obj) -> str | None:
    # def get_logo_url(self, obj):

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
    @extend_schema_field(OpenApiTypes.URI)
    def get_logo_url(self, obj) -> str | None:
    # def get_logo_url(self, obj):

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
# Delivery Partner List Serializer
# =============================================================================

class DeliveryPartnerListSerializer(serializers.ModelSerializer):

    class Meta:

        model = DeliveryPartner

        fields = [

            "id",

            "name",

            "phone",

            "photo",

            "vehicle_type",

            "vehicle_number",

            "is_available",

            "is_active",

            "rating",

            "completed_orders",
        ]

# =============================================================================
# Delivery Assignment Serializer
# =============================================================================

class DeliveryAssignmentSerializer(serializers.ModelSerializer):

    delivery_partner = DeliveryPartnerListSerializer(
        read_only=True
    )

    delivery_partner_id = serializers.PrimaryKeyRelatedField(
        queryset=DeliveryPartner.objects.all(),
        source="delivery_partner",
        write_only=True,
    )

    class Meta:
        model = Order

        fields = [
            "delivery_partner",
            "delivery_partner_id",
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
# Delivery Partner Serializer
# =============================================================================

class DeliveryPartnerSerializer(serializers.ModelSerializer):
    """
    Complete Delivery Partner serializer.
    """

    class Meta:
        model = DeliveryPartner

        fields = [
            "id",

            "restaurant",

            "name",
            "phone",
            "photo",

            "vehicle_type",
            "vehicle_number",

            "rating",
            "completed_orders",

            "current_latitude",
            "current_longitude",

            "is_available",
            "is_active",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "rating",
            "completed_orders",
            "created_at",
            "updated_at",
        ]

    # -------------------------------------------------
    # Phone Validation
    # -------------------------------------------------

    def validate_phone(self, value):

        value = value.strip()

        if len(value) < 8:
            raise serializers.ValidationError(
                "Invalid phone number."
            )

        return value
    
# =============================================================================
# Delivery Partner Location Serializer
# =============================================================================

class DeliveryPartnerLocationSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = DeliveryPartner

        fields = [

            "current_latitude",

            "current_longitude",

        ]

    # ---------------------------------------------
    # Latitude
    # ---------------------------------------------

    def validate_current_latitude(
        self,
        value,
    ):

        if value is None:
            return value

        if value < -90 or value > 90:

            raise serializers.ValidationError(
                "Latitude must be between -90 and 90."
            )

        return value

    # ---------------------------------------------
    # Longitude
    # ---------------------------------------------

    def validate_current_longitude(
        self,
        value,
    ):

        if value is None:
            return value

        if value < -180 or value > 180:

            raise serializers.ValidationError(
                "Longitude must be between -180 and 180."
            )

        return value
    
# =============================================================================
# Delivery Availability Serializer
# =============================================================================

class DeliveryAvailabilitySerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = DeliveryPartner

        fields = [

            "is_available",

            "is_active",

        ]
        
# =============================================================================
# Delivery Partner Tracking Serializer
# =============================================================================

class DeliveryPartnerTrackingSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = DeliveryPartner

        fields = [

            "id",

            "name",

            "phone",

            "current_latitude",

            "current_longitude",

            "is_available",

            "vehicle_type",

            "vehicle_number",
        ]
    
# =============================================================================
# Kitchen Display System (KDS) Serializer
# =============================================================================

class KDSSerializer(serializers.ModelSerializer):
    """
    Primary serializer used by the
    Kitchen Display System.

    Exposes all information required by
    kitchen staff while keeping customer-
    facing fields read-only.

    Used By
    -------
    • Kitchen Dashboard

    • Kitchen Order Queue

    • Order Details

    • Live Kitchen Monitor
    """

    # ==========================================================
    # Computed Fields
    # ==========================================================

    table_number = serializers.SerializerMethodField()

    delivery_partner = serializers.SerializerMethodField()

    items_count = serializers.SerializerMethodField()

    total_quantity = serializers.SerializerMethodField()

    elapsed_minutes = serializers.SerializerMethodField()

    is_overdue = serializers.SerializerMethodField()

    estimated_remaining_minutes = serializers.SerializerMethodField()

    customer_display = serializers.SerializerMethodField()

    status_badge = serializers.SerializerMethodField()

    # ==========================================================
    # Nested Items
    # ==========================================================

    order_items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    # ==========================================================
    # Meta
    # ==========================================================

    class Meta:

        model = Order

        fields = [

            # Identity

            "id",

            "order_number",

            # Restaurant

            "restaurant",

            "table",

            "table_number",

            # Customer

            "customer_name",

            "customer_phone",

            "customer_display",

            # Order

            "order_type",

            "status",

            "kitchen_status",

            "kitchen_priority",

            "kitchen_notes",

            # Kitchen Timeline

            "kitchen_started_at",

            "kitchen_ready_at",

            "served_at",

            "estimated_ready_time",

            # Delivery

            "delivery_status",

            "delivery_partner",

            # Payment

            "payment_status",

            # Totals

            "subtotal",

            "tax_amount",

            "packing_charge",

            "discount_amount",

            "tip_amount",

            "grand_total",

            # Items

            "order_items",

            "items_count",

            "total_quantity",

            # Status Helpers

            "elapsed_minutes",

            "estimated_remaining_minutes",

            "is_overdue",

            "status_badge"

            # Audit

            "created_at",

            "completed_at",

        ]

        read_only_fields = [

            "id",

            "order_number",

            "restaurant",

            "table_number",

            "customer_display",

            "delivery_partner",

            "order_items",

            "items_count",

            "total_quantity",

            "elapsed_minutes",

            "estimated_remaining_minutes",

            "is_overdue",

            "status_badge"

            "created_at",

            "completed_at",

        ]
        
    # ==========================================================
    # Table Number
    # ==========================================================

    def get_table_number(
        self,
        obj,
    ):

        if obj.table:

            return obj.table.table_number

        return None

    # ==========================================================
    # Delivery Partner
    # ==========================================================

    def get_delivery_partner(
        self,
        obj,
    ):

        partner = obj.delivery_partner

        if not partner:

            return None

        return {

            "id": partner.id,

            "name": partner.full_name,

            "phone": partner.phone,

            "vehicle_type": partner.vehicle_type,

            "vehicle_number": partner.vehicle_number,

            "is_available": partner.is_available,
            
            "photo": (
                        partner.profile_photo.url
                        if partner.profile_photo
                        else None
                    ),

        }

    # ==========================================================
    # Items Count
    # ==========================================================

    def get_items_count(self, obj):
        return getattr(obj, "items_count", obj.order_items.count())


    # ==========================================================
    # Total Quantity
    # ==========================================================

    def get_total_quantity(
        self,
        obj,
    ):

        quantity = getattr(
            obj,
            "total_quantity",
            None,
        )

        if quantity is not None:

            return quantity

        return (

            obj.order_items.aggregate(

                total=Sum("quantity")

            )["total"]

            or 0

        )

    # ==========================================================
    # Elapsed Minutes
    # ==========================================================

    def get_elapsed_minutes(
        self,
        obj,
    ):

        if not obj.created_at:

            return 0

        now = timezone.now()

        elapsed = now - obj.created_at

        return int(
            elapsed.total_seconds() / 60
        )
        
        
    # ==========================================================
    # Is Overdue
    # ==========================================================

    def get_is_overdue(
        self,
        obj,
    ):
        """
        Determines whether the order has
        exceeded its estimated ready time.
        """

        if not obj.estimated_ready_time:

            return False

        if obj.kitchen_status in [

            "ready",

            "served",

        ]:

            return False

        return timezone.now() > obj.estimated_ready_time

    # ==========================================================
    # Estimated Remaining Minutes
    # ==========================================================

    def get_estimated_remaining_minutes(
        self,
        obj,
    ):
        """
        Returns the remaining preparation
        time in minutes.

        Returns

        • None if no ETA exists

        • 0 if overdue

        • Positive minutes remaining
        """

        if not obj.estimated_ready_time:

            return None

        remaining = (

            obj.estimated_ready_time

            - timezone.now()

        ).total_seconds()

        if remaining <= 0:

            return 0

        return int(

            remaining // 60

        )

    # ==========================================================
    # Customer Display
    # ==========================================================

    def get_customer_display(
        self,
        obj,
    ):
        """
        Returns a compact customer string
        suitable for kitchen displays.
        """

        if obj.customer_name:

            if obj.customer_phone:

                return (

                    f"{obj.customer_name}"

                    f" ({obj.customer_phone})"

                )

            return obj.customer_name

        if obj.customer_phone:

            return obj.customer_phone

        return "Walk-in Customer"

    # ==========================================================
    # Status Badge
    # ==========================================================

    def get_status_badge(
        self,
        obj,
    ):
        """
        Returns badge information used by
        the frontend KDS.
        """

        return {

            "label": obj.get_kitchen_status_display(),

            "color": {

                "pending": "secondary",

                "accepted": "primary",

                "preparing": "warning",

                "ready": "success",

                "served": "dark",

            }.get(obj.kitchen_status, "secondary"),

            "priority": obj.kitchen_priority,

            "icon": {

                "pending": "clock",

                "accepted": "check",

                "preparing": "chef-hat",

                "ready": "bell",

                "served": "check-circle",

            }.get(obj.kitchen_status, "clock"),

            "order_status": obj.status,

            "payment_status": obj.payment_status,

            "delivery_status": obj.delivery_status,

            "is_completed": obj.is_completed,

            "is_paid": obj.payment_status == "paid",

            "is_overdue": self.get_is_overdue(obj),

        }

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # This serializer powers the Kitchen
    # Display System (KDS).
    #
    # Business rules:
    #
    # • Kitchen staff should never modify
    #   payment information.
    #
    # • Kitchen updates only:
    #       kitchen_status
    #       kitchen_priority
    #       kitchen_notes
    #       estimated_ready_time
    #
    # • Order completion should be handled
    #   through dedicated KDS services,
    #   not directly from this serializer.
    #
    # • Delivery assignment is managed by
    #   Delivery APIs.
    #
    # • Payment verification is managed by
    #   Payment APIs.
    #
    # • Customer-facing status should stay
    #   synchronized with kitchen_status
    #   via service-layer methods.
    #
    # • Views should use:
    #
    #   select_related(
    #       "table",
    #       "delivery_partner",
    #   )
    #
    #   prefetch_related(
    #       "order_items",
    #       "order_items__food_item",
    #       "order_items__selected_addons",
    #   )
    #
    # to avoid N+1 queries.
    # ==========================================================
    
# ==========================================================
# KDS Order Serializer
# ==========================================================

class KDSOrderSerializer(serializers.ModelSerializer):
    """
    Kitchen Display System order serializer.
    """

    customer_name = serializers.CharField(
        source="customer_name",
        read_only=True,
    )

    table_number = serializers.CharField(
        source="table.table_number",
        read_only=True,
    )

    items = OrderItemSerializer(
        source="order_items",
        many=True,
        read_only=True,
    )

    # Order model stores customer instructions as customer_note.
    # Expose the API's expected special_instructions field through that model field.
    special_instructions = serializers.CharField(
        source="customer_note",
        read_only=True,
    )

    elapsed_minutes = serializers.SerializerMethodField()

    class Meta:

        model = Order

        fields = [

            "id",

            "order_number",

            "customer_name",

            "table_number",

            "order_type",

            "status",

            "kitchen_status",

            "kitchen_priority",

            "special_instructions",

            "items",

            "created_at",

            "elapsed_minutes",

        ]

    def get_elapsed_minutes(
        self,
        obj,
    ):
        """
        Minutes since order creation.
        """

        return int(
            (
                timezone.now() - obj.created_at
            ).total_seconds() // 60
        )
    
# ==============================================================================
# Kitchen Status Serializer
# ==============================================================================

class KDSStatusSerializer(serializers.ModelSerializer):
    """
    Serializer used to update the
    kitchen status of an order.

    Used By
    -------
    • Kitchen Display System

    • Kitchen Queue

    • Chef Dashboard
    """

    class Meta:

        model = Order

        fields = [

            "kitchen_status",

        ]

        extra_kwargs = {

            "kitchen_status": {

                "required": True,

            }

        }

    # ==========================================================
    # Kitchen Status
    # ==========================================================

    def validate_kitchen_status(
        self,
        value,
    ):

        valid_statuses = [

            "pending",

            "accepted",

            "preparing",

            "ready",

            "served",

        ]

        if value not in valid_statuses:

            raise serializers.ValidationError(

                "Invalid kitchen status."

            )

        return value

    # ==========================================================
    # Update
    # ==========================================================
    
    #----I recommend not using this serializer's update() method in your view.........
    def update(
        self,
        instance: Restaurant,
        validated_data: dict,
    ) -> Restaurant:
    
    # def update(
    #     self,
    #     instance,
    #     validated_data,
    # ):
        """
        Kitchen timeline updates are handled
        by the service layer.
        ------------------------------------------------------------------------
        I recommend not using this serializer's update() method in your view - 
        
        Instead, your view should do:

        serializer = KDSStatusSerializer(
            order,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        order = update_kds_status(
            order,
            serializer.validated_data["kitchen_status"],
        )

        where update_kds_status() (in services.py) will:

        Set kitchen_status
        Set kitchen_started_at
        Set kitchen_ready_at
        Set served_at
        Synchronize status if needed
        Set estimated_ready_time
        Trigger notifications/events if required
        -------------------------------------------------------------------------
        
        This serializer only validates data.
        """

        instance.kitchen_status = validated_data[
            "kitchen_status"
        ]

        instance.save(
            update_fields=[
                "kitchen_status",
            ]
        )

        return instance

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # • Views should call the
    #   update_kds_status()
    #   service instead of relying on this
    #   serializer's update() method.
    #
    # • The service is responsible for:
    #
    #     kitchen_started_at
    #
    #     kitchen_ready_at
    #
    #     served_at
    #
    #     estimated_ready_time
    #
    #     status synchronization
    #
    #     notifications
    #
    #     analytics events
    #
    # • This serializer exists mainly for
    #   validation.
    # ==========================================================
    
# ==============================================================================
# Kitchen Priority Serializer
# ==============================================================================

class KDSPrioritySerializer(serializers.ModelSerializer):
    """
    Serializer used to update the
    kitchen priority of an order.

    Used By
    -------
    • Kitchen Display System

    • Kitchen Queue

    • Chef Dashboard

    • Manager Dashboard
    
            -----------------------------------------------------------------------
        Use it like this in your view:

        serializer = KDSPrioritySerializer(
            order,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        order = update_kds_priority(
            order,
            serializer.validated_data["kitchen_priority"],
        )

        This keeps your architecture consistent with:

        update_kds_status()
        assign_delivery_partner()
        update_delivery_status()
        update_partner_location()
        
        where all business logic stays in services.py.
        -------------------------------------------------------------------------
    
    """

    class Meta:

        model = Order

        fields = [

            "kitchen_priority",

        ]

        extra_kwargs = {

            "kitchen_priority": {

                "required": True,

            }

        }

    # ==========================================================
    # Kitchen Priority
    # ==========================================================

    def validate_kitchen_priority(
        self,
        value,
    ):

        valid_priorities = [

            "low",

            "normal",

            "high",

            "urgent",

        ]

        if value not in valid_priorities:

            raise serializers.ValidationError(

                "Invalid kitchen priority."
                
                

            )

        return value

    # ==========================================================
    # Update
    # ==========================================================
    def update(
        self,
        instance: Restaurant,
        validated_data: dict,
    ) -> Restaurant:

    # def update(
    #     self,
    #     instance,
    #     validated_data,
    # ):
        """
        
        Priority updates should normally
        be handled by the service layer.

        This update method exists only as
        a fallback.
        """

        instance.kitchen_priority = validated_data[
            "kitchen_priority"
        ]

        instance.save(
            update_fields=[
                "kitchen_priority",
            ]
        )

        return instance

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # • Views should call
    #   update_kds_priority()
    #   instead of relying on
    #   serializer.update().
    #
    # • Future responsibilities of the
    #   service may include:
    #
    #     • Audit logging
    #
    #     • Manager approval
    #
    #     • Notification broadcasting
    #
    #     • Queue reordering
    #
    #     • Analytics events
    #
    # This serializer is responsible
    # only for validation.
    # ==========================================================

# =============================================================================
# KDS Note Serializer
# =============================================================================

class KDSNoteSerializer(serializers.ModelSerializer):
    """
    Serializer for Kitchen Display System notes.
    
    End Point: POST /orders/<order_id>/notes/
    
    Expected request
    
    {
        "note": "No onions. Customer has an allergy.",
        "note_type": "allergy",
        "is_pinned": true,
        "is_internal": true
    }
    
    Response
    
    {
        "id": 12,
        "staff": 5,
        "staff_name": "John Doe",
        "note": "No onions. Customer has an allergy.",
        "note_type": "allergy",
        "is_pinned": true,
        "is_internal": true,
        "created_at": "2026-07-10T12:15:40Z",
        "updated_at": "2026-07-10T12:15:40Z",
        "edited_by": null,
        "edited_by_name": null,
        "edited_at": null,
        "edited_reason": ""
    }
    
    """

    staff_name = serializers.CharField(
        
        source="staff.full_name",
        
        read_only=True,
        
    )

    edited_by_name = serializers.CharField(
        
        source="edited_by.full_name",
        
        read_only=True,
        
    )

    class Meta:
        model = KitchenNote

        fields = [
            "id",

            "staff",
            "staff_name",

            "note",
            "note_type",

            "is_pinned",
            "is_internal",

            "created_at",
            "updated_at",

            "edited_by",
            "edited_by_name",
            "edited_at",
            "edited_reason",
        ]

        read_only_fields = [
            "id",

            "staff",
            "staff_name",

            "created_at",
            "updated_at",

            "edited_by",
            "edited_by_name",
            "edited_at",
        ]

# =============================================================================
# KDS Statistics Serializer
# =============================================================================

class KDSStatisticsSerializer(serializers.Serializer):
    """
    Kitchen Display System statistics.
    
    Expected service output:
    
    Your services.py can simply return a dictionary:

    return {
        "pending_orders": 5,
        "accepted_orders": 3,
        "preparing_orders": 8,
        "ready_orders": 4,
        "served_orders": 18,
        "total_active_orders": 20,
        "high_priority_orders": 2,
        "urgent_priority_orders": 1,
        "average_preparation_time": 14.6,
    }

    Then in the view:

    stats = get_kds_statistics(restaurant)

    serializer = KDSStatisticsSerializer(stats)

    return Response(serializer.data)

    This follows your service-layer architecture cleanly:
    
    """

    pending_orders = serializers.IntegerField(read_only=True)

    accepted_orders = serializers.IntegerField(read_only=True)

    preparing_orders = serializers.IntegerField(read_only=True)

    ready_orders = serializers.IntegerField(read_only=True)

    served_orders = serializers.IntegerField(read_only=True)

    total_active_orders = serializers.IntegerField(read_only=True)

    high_priority_orders = serializers.IntegerField(read_only=True)

    urgent_priority_orders = serializers.IntegerField(read_only=True)

    average_preparation_time = serializers.FloatField(read_only=True)

# ==========================================================
# Staff Shift Schedule Serializer
# ==========================================================

class StaffShiftScheduleSerializer(serializers.ModelSerializer):

    class Meta:

        model = StaffShiftSchedule

        fields = [

            "id",

            "staff",

            "day_of_week",

            "shift_start",

            "shift_end",

            "is_off_day",

            "is_active",

        ]

    def validate(self, attrs):

        shift_start = attrs.get(
            "shift_start",
            getattr(self.instance, "shift_start", None),
        )

        shift_end = attrs.get(
            "shift_end",
            getattr(self.instance, "shift_end", None),
        )

        is_off_day = attrs.get(
            "is_off_day",
            getattr(self.instance, "is_off_day", False),
        )

        if (
            not is_off_day
            and shift_start
            and shift_end
            and shift_start >= shift_end
        ):
            raise serializers.ValidationError(
                "Shift end time must be after shift start time."
            )

        return attrs
    
# =============================================================================
# Staff Serializer
# =============================================================================

class StaffSerializer(serializers.ModelSerializer):
    """
    Full serializer for Restaurant Staff.

    Used By

    • Staff CRUD

    • Staff Profile

    • Staff Details

    • Dashboard
    """

    full_name = serializers.ReadOnlyField()
    
    has_login = serializers.ReadOnlyField()
    
    staff_status = serializers.SerializerMethodField()
    
    shift_schedules = StaffShiftScheduleSerializer(
        
        many=True,
        
        read_only=True,
        
    )

    class Meta:

        model = Staff

        fields = [

            # Identity

            "id",

            "restaurant",

            "user",
            
            "has_login",

            "employee_id",

            # Personal

            "first_name",

            "last_name",

            "full_name",

            "profile_photo",

            # Contact

            "country_code",

            "phone",

            "alternate_phone",

            "email",

            # Employment

            "role",

            "designation",

            "joining_date",

            "salary",

            # Shift
            
            "shift_schedules",

            "is_on_shift",

            "is_on_break",

            "last_shift_started_at",

            "last_shift_ended_at",

            # Status

            "staff_status",
            
            "is_active",

            "is_deleted",

            "resigned_at",

            "notes",

            "last_login_at",

            # Audit

            "created_at",

            "updated_at",

        ]

        read_only_fields = [

            "id",
            
            "user",
            
            "has_login",
            
            "restaurant",

            "full_name",

            "created_at",

            "updated_at",

            "last_login_at",

            "last_shift_started_at",

            "last_shift_ended_at",
            
            "staff_status",

        ]
        
    # ==========================================================
    # Staff Status
    # ==========================================================

    def get_staff_status(self, obj):

        if not obj.is_active:

            return "inactive"

        if obj.is_on_break:

            return "on_break"

        if obj.is_on_shift:

            return "on_shift"

        return "off_shift"

    # ==========================================================
    # Employee ID
    # ==========================================================

    def validate_employee_id(self, value):

        value = value.strip().upper()

        if len(value) < 2:

            raise serializers.ValidationError(

                "Employee ID is too short."

            )

        return value

    # ==========================================================
    # Phone
    # ==========================================================

    def validate_phone(self, value):

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
    # Validate Alternate Phone
    # ==========================================================
    
    def validate_alternate_phone(self, value):

        if not value:

            return value

        digits = "".join(
            c
            for c in value
            if c.isdigit()
        )

        if len(digits) < 8:

            raise serializers.ValidationError(
                "Invalid alternate phone number."
            )

        return value
    
    # ==========================================================
    # Validate Country Code
    # ==========================================================
    
    def validate_country_code(self, value):

        value = value.strip()

        if not value.startswith("+"):

            raise serializers.ValidationError(
                "Country code must start with '+'."
            )

        return value

    # ==========================================================
    # Salary
    # ==========================================================

    def validate_salary(self, value):

        if value is not None and value < 0:

            raise serializers.ValidationError(

                "Salary cannot be negative."

            )

        return value
    
    # ==========================================================
    # Designation
    # ==========================================================

    def validate_designation(self, value):

        return value.strip()
    
    # ==========================================================
    # Email
    # ==========================================================

    def validate_email(self, value):

        if value:

            value = value.strip().lower()

        return value
    
    # ==========================================================
    # First Name
    # ==========================================================

    def validate_first_name(self, value):

        value = value.strip()

        if len(value) < 2:

            raise serializers.ValidationError(

                "First name is too short."

            )

        return value


    # ==========================================================
    # Last Name
    # ==========================================================

    def validate_last_name(self, value):

        return value.strip()
    
    # ==========================================================
    # Notes
    # ==========================================================

    def validate_notes(self, value):

        return value.strip()

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Staff role permissions are enforced
    # in the View/Permission layer.
    #
    # This serializer validates data only.
    #
    # ==========================================================
    #     One future improvement (don't do it now)
    # --------------------------------------------------

    # Later, when you build the Staff APIs, you can remove the duplicated get_staff_status() from both serializers by creating a small mixin:

    # class StaffStatusMixin:

    #     def get_staff_status(self, obj):

    #         if not obj.is_active:
    #             return "inactive"

    #         if obj.is_on_break:
    #             return "on_break"

    #         if obj.is_on_shift:
    #             return "on_shift"

    #         return "off_shift"

    # Then:

    # class StaffSerializer(
    #     StaffStatusMixin,
    #     serializers.ModelSerializer,
    # ):

    # and

    # class StaffListSerializer(
    #     StaffStatusMixin,
    #     serializers.ModelSerializer,
    # ):

    # This avoids duplicating the method. It's a clean refactor for later, but not necessary now.
    
# =============================================================================
# Staff List Serializer
# =============================================================================

class StaffListSerializer(serializers.ModelSerializer):
    
    """
    Lightweight serializer for
    listing staff members.
    """

    full_name = serializers.ReadOnlyField()
    
    has_login = serializers.ReadOnlyField()
    
    staff_status = serializers.SerializerMethodField()

    class Meta:

        model = Staff

        fields = [

            "id",
            
            "restaurant",

            "employee_id",

            "full_name",
            
            "has_login",

            "profile_photo",

            "role",

            "designation",

            "phone",

            "is_on_shift",

            "is_on_break",

            "is_active",
            
            "staff_status",

        ]
        
        read_only_fields = [

            "staff_status",

        ]
        
    def get_staff_status(self, obj):

        if not obj.is_active:

            return "inactive"

        if obj.is_on_break:

            return "on_break"

        if obj.is_on_shift:

            return "on_shift"

        return "off_shift"

# =============================================================================
# Staff Shift Serializer
# =============================================================================

class StaffShiftSerializer(serializers.Serializer):
    """
    Serializer used for
    staff shift actions.
    """

    ACTION_CHOICES = [

        ("clock_in", "Clock In"),

        ("clock_out", "Clock Out"),

        ("start_break", "Start Break"),

        ("end_break", "End Break"),

    ]

    action = serializers.ChoiceField(

        choices=ACTION_CHOICES,

    )

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Business logic is handled
    # by the service layer.
    #
    # ==========================================================

    # ==========================================================
    # Staff Status
    # ==========================================================

    def get_staff_status(self, obj):

        if not obj.is_active:

            return "inactive"

        if obj.is_on_break:

            return "on_break"

        if obj.is_on_shift:

            return "on_shift"

        return "off_shift"

    # ==========================================================
    # Shift Validation
    # ==========================================================

    def validate(self, attrs):

        shift_start = attrs.get(
            "shift_start",
            getattr(
                self.instance,
                "shift_start",
                None,
            ),
        )

        shift_end = attrs.get(
            "shift_end",
            getattr(
                self.instance,
                "shift_end",
                None,
            ),
        )

        if (

            shift_start

            and shift_end

            and shift_start >= shift_end

        ):

            raise serializers.ValidationError(

                "Shift end time must be after shift start time."

            )

        return attrs

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Shift clock-in/clock-out timestamps
    # should be updated through the
    # service layer.
    #
    # ==========================================================
    
# ==========================================================
# Staff Role Serializer
# ==========================================================

class StaffRoleSerializer(serializers.ModelSerializer):
    """
    Serializer used to update staff roles.

    Used By

    • Manager Panel

    • Staff Administration

    • Permissions
    """

    class Meta:

        model = Staff

        fields = [

            "role",

        ]

    # ==========================================================
    # Enterprise Notes
    # ==========================================================
    #
    # Role changes should be performed
    # only by restaurant owners or
    # managers.
    #
    # Permissions should be enforced
    # in the View/Permission layer.
    #
    # ==========================================================
    # Since you've adopted a service-layer architecture (assign_delivery_partner(), update_delivery_status(), etc.), I'd follow the same pattern here and create:

    # update_staff_shift(staff, data)
    # update_staff_role(staff, role)

    # in services.py.

    # The serializers should remain responsible only for validation, while the services handle business logic such as:

    # updating last_shift_started_at
    # updating last_shift_ended_at
    # clearing is_on_break when a shift ends
    # recording audit logs
    # triggering notifications if needed

    # This keeps your backend consistent and makes future changes easier.
    
    #===========================================================


# ==========================================================
# Staff Attendance Serializer
# ==========================================================

class StaffAttendanceSerializer(serializers.ModelSerializer):
    """
    Staff attendance serializer.
    """

    staff_name = serializers.CharField(
        source="staff.full_name",
        read_only=True,
    )

    employee_id = serializers.CharField(
        source="staff.employee_id",
        read_only=True,
    )

    class Meta:
        model = StaffAttendance

        fields = [

            "id",

            "staff",
            "staff_name",
            "employee_id",

            "attendance_date",

            "status",

            "clock_in",
            "clock_out",

            "worked_minutes",
            "break_minutes",
            "late_minutes",
            "overtime_minutes",

            "notes",

            "created_at",
            "updated_at",

        ]

        read_only_fields = [

            "id",

            "staff_name",
            "employee_id",

            "worked_minutes",
            "break_minutes",
            "late_minutes",
            "overtime_minutes",

            "created_at",
            "updated_at",

        ]

# ==========================================================
# Clock In Serializer
# ==========================================================

class AttendanceClockInSerializer(serializers.Serializer):
    """
    Clock in request serializer.
    """

    staff_id = serializers.IntegerField()

# ==========================================================
# Clock Out Serializer
# ==========================================================

class AttendanceClockOutSerializer(serializers.Serializer):
    """
    Clock out request serializer.
    """

    staff_id = serializers.IntegerField()

# ==========================================================
# Attendance Status Serializer
# ==========================================================

class AttendanceStatusSerializer(serializers.Serializer):
    """
    Update attendance status.
    """

    status = serializers.ChoiceField(
        choices=StaffAttendance.STATUS_CHOICES,
    )

# ==========================================================
# Attendance Notes Serializer
# ==========================================================

class AttendanceNotesSerializer(serializers.Serializer):
    """
    Update attendance notes.
    """

    notes = serializers.CharField(
        
        allow_blank=True,
    )
    
    """
    Why split them?

    This keeps each endpoint focused:

    StaffAttendanceSerializer → GET attendance / attendance detail
    AttendanceClockInSerializer → POST /attendance/clock-in/
    AttendanceClockOutSerializer → POST /attendance/clock-out/
    AttendanceStatusSerializer → PATCH attendance status
    AttendanceNotesSerializer → PATCH attendance notes
    
    """
    
# ==========================================================
# Staff Attendance Update Serializer
# ==========================================================

class StaffAttendanceUpdateSerializer(serializers.Serializer):
    """
    Update a staff attendance record.
    """

    status = serializers.ChoiceField(
        choices=StaffAttendance.STATUS_CHOICES,
        required=False,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    
    
# ==========================================================
# Staff Break Serializer
# ==========================================================

class StaffBreakSerializer(serializers.ModelSerializer):
    """
    Serializer for staff break history.
    
    StaffBreakSerializer

    Used for:

    GET /staff/breaks/
    POST /staff/break/start/ response
    POST /staff/break/end/ response

    The client never edits a break directly, so everything is read-only.
    ----------------------------
    BreakStartSerializer

    Request:

    {
        "staff_id": 5
    }
    ----------------------------
    BreakEndSerializer

    Request:

    {
        "staff_id": 5
    }
    ----------------------------
    """

    staff_id = serializers.IntegerField(
        source="attendance.staff.id",
        read_only=True,
    )

    staff_name = serializers.CharField(
        source="attendance.staff.full_name",
        read_only=True,
    )

    attendance_id = serializers.IntegerField(
        source="attendance.id",
        read_only=True,
    )

    class Meta:
        model = StaffBreak

        fields = [

            "id",

            "attendance_id",

            "staff_id",
            "staff_name",

            "break_start",
            "break_end",

            "minutes",

            "is_active",

            "created_at",
            "updated_at",

        ]

        read_only_fields = [

            "id",

            "attendance_id",

            "staff_id",
            "staff_name",

            "break_start",
            "break_end",

            "minutes",

            "is_active",

            "created_at",
            "updated_at",

        ]

# ==========================================================
# Break Start Serializer
# ==========================================================

class BreakStartSerializer(serializers.Serializer):
    """
    Start a staff break.
    """

    staff_id = serializers.IntegerField()

# ==========================================================
# Break End Serializer
# ==========================================================

class BreakEndSerializer(serializers.Serializer):
    """
    End a staff break.
    """

    staff_id = serializers.IntegerField()
    
# ==========================================================
# Break Filter Serializer
# ==========================================================

class BreakFilterSerializer(serializers.Serializer):
    
    attendance_id = serializers.IntegerField(required=False)
    
    staff_id = serializers.IntegerField(required=False)
    
    today = serializers.BooleanField(required=False, default=False)
    
# ==========================================================
# Kitchen Note Create Serializer
# ==========================================================

class KitchenNoteCreateSerializer(serializers.Serializer):
    """
    Create a kitchen note.
    
    Why these serializers?
    
    KitchenNoteCreateSerializer

    Used by:
    POST /api/kitchen/notes/

    Request:

    {
        "order_id": 15,
        "note": "No onion",
        "note_type": "customer",
        "is_internal": false,
        "is_pinned": true
    }
    -------------------------------------------------------------
    
    KitchenNoteUpdateSerializer
    ---------------------------
    Used by:
    PATCH /api/kitchen/notes/8/

    Example:

    {
        "note": "Extra spicy",
        "edited_reason": "Customer changed request"
    }
    
    -------------------------------------------------------------
    Everything is optional because it's a PATCH request.
    -------------------------------------------------------------
    
    KitchenNoteFilterSerializer
    ---------------------------
    Used by:
    GET /api/kitchen/notes/?order_id=15&is_internal=true

    or

    GET /api/kitchen/notes/?note_type=chef

    ----------------------------------------------------------------------
    The validated data can be passed directly to your service:

    filter_serializer = KitchenNoteFilterSerializer(
        data=request.query_params,
    )

    filter_serializer.is_valid(
        raise_exception=True,
    )

    notes = list_notes(
        restaurant=restaurant,
        **filter_serializer.validated_data,
    )
    
    ----------------------------------------------------------------------
    This keeps the same pattern you've been following across the project:
    
    Action-specific serializers (Create, Update, Filter)
    Thin views
    Business logic in services
    Validation centralized in serializers
    
    """

    order_id = serializers.IntegerField()

    note = serializers.CharField(
        trim_whitespace=True,
    )

    note_type = serializers.ChoiceField(
        choices=KitchenNote.NOTE_TYPES,
        default="general",
    )

    is_internal = serializers.BooleanField(
        default=True,
    )

    is_pinned = serializers.BooleanField(
        default=False,
    )

    def validate_note(self, value):

        value = value.strip()

        if not value:

            raise serializers.ValidationError(
                "Note cannot be empty."
            )

        return value
    
# ==========================================================
# Kitchen Note Update Serializer
# ==========================================================

class KitchenNoteUpdateSerializer(serializers.Serializer):
    """
    Update a kitchen note.
    """

    note = serializers.CharField(
        required=False,
        trim_whitespace=True,
    )

    note_type = serializers.ChoiceField(
        choices=KitchenNote.NOTE_TYPES,
        required=False,
    )

    is_internal = serializers.BooleanField(
        required=False,
    )

    is_pinned = serializers.BooleanField(
        required=False,
    )

    edited_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )

    def validate_note(self, value):

        value = value.strip()

        if not value:

            raise serializers.ValidationError(
                "Note cannot be empty."
            )

        return value

# ==========================================================
# Kitchen Note Filter Serializer
# ==========================================================

class KitchenNoteFilterSerializer(serializers.Serializer):
    """
    Filter kitchen notes.
    """

    order_id = serializers.IntegerField(
        required=False,
    )

    note_type = serializers.ChoiceField(
        choices=KitchenNote.NOTE_TYPES,
        required=False,
    )

    is_internal = serializers.BooleanField(
        required=False,
    )

    is_pinned = serializers.BooleanField(
        required=False,
    )
    
# =============================================================================
# Audit Log Serializer
# =============================================================================

class AuditLogSerializer(serializers.ModelSerializer):
    
    """
    Read-only serializer for audit logs.
    
    Filter audit logs.
    
    AuditLogSerializer
    ------------------
    Used for:
    GET /api/audit-logs/

    Returns:

    {
        "id": 51,
        "restaurant": 1,
        "restaurant_name": "Pizza Hub",
        "staff": 4,
        "staff_name": "John",
        "action": "staff_created",
        "action_display": "Staff Created",
        "entity": "Staff",
        "entity_id": 12,
        "description": "Created staff member Alice.",
        "ip_address": "192.168.1.20",
        "user_agent": "...",
        "created_at": "2026-07-10T12:40:00Z"
    }
    
    
    AuditLogFilterSerializer
    ------------------------
    Used by:
    GET /api/audit-logs/

    ?action=clock_in
    &staff_id=5
    &entity=Staff
    &from_date=2026-07-01
    &to_date=2026-07-10


    -------------------------------------------------
    The view simply does:

    filter_serializer = AuditLogFilterSerializer(
        data=request.query_params,
    )

    filter_serializer.is_valid(
        raise_exception=True,
    )

    logs = get_audit_logs(
        restaurant=restaurant,
        **filter_serializer.validated_data,
    )
    
    -------------------------------------------------
    """

    staff_name = serializers.CharField(
        source="staff.full_name",
        read_only=True,
    )

    restaurant_name = serializers.CharField(
        source="restaurant.name",
        read_only=True,
    )

    action_display = serializers.CharField(
        source="get_action_display",
        read_only=True,
    )

    class Meta:

        model = AuditLog

        fields = [

            "id",

            "restaurant",

            "restaurant_name",

            "staff",

            "staff_name",

            "action",

            "action_display",

            "entity",

            "entity_id",

            "description",

            "ip_address",

            "user_agent",

            "created_at",

        ]

        read_only_fields = fields
            
# =============================================================================
# Audit Log Filter Serializer
# =============================================================================

class AuditLogFilterSerializer(serializers.Serializer):
    
    """
    Filter audit logs.
    
    --------------------------------------------------------------------------------------------------------------
    View response
    
    {
        "id": 51,
        "restaurant_name": "Pizza Hub",
        "staff_name": "John",
        "action": "staff_created",
        "action_display": "Staff Created",
        "entity": "Staff",
        "entity_id": 12,
        "description": "Created staff member Alice.",
        "ip_address": "192.168.1.20",
        "user_agent": "Mozilla/5.0...",
        "created_at": "2026-07-10T14:30:18Z"
    }
    
    --------------------------------------------------------------------------------------------------------------
    Filtering
    
    GET /api/audit-logs/?staff_id=5

    GET /api/audit-logs/?action=clock_in

    GET /api/audit-logs/?entity=Order

    GET /api/audit-logs/?entity_id=42

    GET /api/audit-logs/?from_date=2026-07-01&to_date=2026-07-10

    The AuditLogFilterSerializer validates those query parameters, and your get_audit_logs() service receives 
    properly typed, validated values.

    This design keeps the API focused on viewing audit history while ensuring all audit creation 
    continues to go through the service layer, which is exactly the separation of responsibilities 
    you've been building throughout ZenQRMenu.
    -------------------------------------------------------------------------------------------------------------
    """

    action = serializers.ChoiceField(
        choices=AuditLog.Action.choices,
        required=False,
    )

    entity = serializers.CharField(
        required=False,
    )

    entity_id = serializers.IntegerField(
        required=False,
    )

    staff_id = serializers.IntegerField(
        required=False,
    )

    from_date = serializers.DateField(
        required=False,
    )

    to_date = serializers.DateField(
        required=False,
    )

    def validate(self, attrs):

        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")

        if (
            from_date
            and
            to_date
            and
            from_date > to_date
        ):

            raise serializers.ValidationError(
                "from_date cannot be after to_date."
            )

        return attrs
    
# =============================================================================
# Review Serializers
# =============================================================================


class ReviewSerializer(serializers.Serializer):
    """
    Public review representation returned by the Review APIs.

    Matches ReviewListCreateAPIView.serialize().
    """

    id = serializers.IntegerField()
    customer_name = serializers.CharField()
    rating = serializers.IntegerField()
    comment = serializers.CharField()
    owner_response = serializers.CharField()
    created_at = serializers.DateTimeField()


class ReviewListResponseSerializer(serializers.Serializer):
    """
    Response returned by:
        GET /api/restaurants/{restaurant_id}/reviews/
    """

    success = serializers.BooleanField()
    count = serializers.IntegerField()
    average_rating = serializers.FloatField()
    reviews = ReviewSerializer(many=True)


class ReviewCreateRequestSerializer(serializers.Serializer):
    """
    Request accepted by:
        POST /api/restaurants/{restaurant_id}/reviews/
    """

    order_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    customer_name = serializers.CharField(
        required=False,
        max_length=120,
    )

    customer_email = serializers.EmailField(
        required=False,
        allow_blank=True,
    )

    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=True,
    )

    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class ReviewResponseSerializer(serializers.Serializer):
    """
    Response returned after creating/updating a review.
    """

    success = serializers.BooleanField()
    review = ReviewSerializer()


class ReviewUpdateRequestSerializer(serializers.Serializer):
    """
    Request accepted by:
        PATCH /api/reviews/{review_id}/

    The actual ReviewDetailAPIView only processes these two fields.
    """

    owner_response = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    is_published = serializers.BooleanField(
        required=False,
    )
    
    
