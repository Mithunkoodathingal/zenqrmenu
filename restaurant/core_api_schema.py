"""OpenAPI contracts for the legacy/core endpoints in restaurant.views.views.

This module changes schema generation only. Runtime view logic remains untouched.
It is loaded from AppConfig.ready() so drf-spectacular sees the extensions while
building the schema.
"""

from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from restaurant.core_api_serializers import (
    AIMenuExtractRequestSerializer,
    AIMenuExtractResponseSerializer,
    AIImageSearchResponseSerializer,
    CategoryCreateRequestSerializer,
    CategoryPayloadSerializer,
    CategorySuccessResponseSerializer,
    ErrorResponseSerializer,
    MenuItemCreateRequestSerializer,
    MenuItemCreateResponseSerializer,
    MenuItemPayloadSerializer,
    MenuItemUpdateRequestSerializer,
    PublicOrderDetailResponseSerializer,
    RestaurantProfileRequestSerializer,
    RestaurantProfileResponseSerializer,
    RestaurantProfileSaveResponseSerializer,
    TableCreateRequestSerializer,
    TableCreateResponseSerializer,
    TablePayloadSerializer,
)
from restaurant.serializers import (
    ErrorSerializer,
    RestaurantDetailResponseSerializer,
    RestaurantSerializer,
)


# =============================================================================
# Class-based core endpoints
# =============================================================================


class MyRestaurantSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.MyRestaurantAPIView"

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(
                tags=["Restaurant"],
                operation_id="Restaurant_MyRestaurant",
                summary="Get My Restaurant",
                description="Return the authenticated user's restaurant.",
                responses={
                    200: RestaurantSerializer,
                    401: ErrorSerializer,
                    404: ErrorSerializer,
                },
            )
            def get(self, request, *args, **kwargs):
                pass

        return Fixed


class UpdateRestaurantSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.UpdateRestaurantAPIView"

    def view_replacement(self):
        class Fixed(self.target_class):
            @extend_schema(
                tags=["Restaurant"],
                operation_id="Restaurant_Update",
                summary="Update Restaurant",
                description="Fully update a restaurant owned by the authenticated user.",
                request=RestaurantSerializer,
                responses={
                    200: RestaurantSerializer,
                    400: ErrorSerializer,
                    401: ErrorSerializer,
                    403: ErrorSerializer,
                    404: ErrorSerializer,
                },
                parameters=[
                    OpenApiParameter(
                        name="restaurant_id",
                        type=OpenApiTypes.INT,
                        location=OpenApiParameter.PATH,
                        required=True,
                        description="Restaurant primary key.",
                    )
                ],
            )
            def put(self, request, *args, **kwargs):
                pass

            @extend_schema(
                tags=["Restaurant"],
                operation_id="Restaurant_PartialUpdate",
                summary="Partially Update Restaurant",
                description="Partially update a restaurant owned by the authenticated user.",
                request=RestaurantSerializer,
                responses={
                    200: RestaurantSerializer,
                    400: ErrorSerializer,
                    401: ErrorSerializer,
                    403: ErrorSerializer,
                    404: ErrorSerializer,
                },
                parameters=[
                    OpenApiParameter(
                        name="restaurant_id",
                        type=OpenApiTypes.INT,
                        location=OpenApiParameter.PATH,
                        required=True,
                        description="Restaurant primary key.",
                    )
                ],
            )
            def patch(self, request, *args, **kwargs):
                pass

        return Fixed


# =============================================================================
# Categories
# =============================================================================


class CategoriesSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.categories_api"

    def view_replacement(self):
        return extend_schema(
            methods=["GET"],
            tags=["Menu"],
            operation_id="Category_List",
            summary="List Categories",
            responses={
                200: CategoryPayloadSerializer(many=True),
                401: ErrorResponseSerializer,
                404: ErrorResponseSerializer,
            },
        )(
            extend_schema(
                methods=["POST"],
                tags=["Menu"],
                operation_id="Category_Create",
                summary="Create Category",
                request=CategoryCreateRequestSerializer,
                responses={
                    201: CategoryPayloadSerializer,
                    400: ErrorResponseSerializer,
                    401: ErrorResponseSerializer,
                    404: ErrorResponseSerializer,
                },
            )(self.target_class)
        )


class CategoryDetailSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.category_detail_api"

    def view_replacement(self):
        return extend_schema(
            methods=["PATCH"],
            tags=["Menu"],
            operation_id="Category_Update",
            summary="Update Category",
            request=CategoryCreateRequestSerializer,
            responses={
                200: CategoryPayloadSerializer,
                401: ErrorResponseSerializer,
                404: ErrorResponseSerializer,
            },
            parameters=[
                OpenApiParameter(
                    name="id",
                    type=OpenApiTypes.INT,
                    location=OpenApiParameter.PATH,
                    required=True,
                    description="Category primary key.",
                )
            ],
        )(
            extend_schema(
                methods=["DELETE"],
                tags=["Menu"],
                operation_id="Category_Delete",
                summary="Delete Category",
                responses={
                    200: CategorySuccessResponseSerializer,
                    401: ErrorResponseSerializer,
                    404: ErrorResponseSerializer,
                },
                parameters=[
                    OpenApiParameter(
                        name="id",
                        type=OpenApiTypes.INT,
                        location=OpenApiParameter.PATH,
                        required=True,
                        description="Category primary key.",
                    )
                ],
            )(self.target_class)
        )


# =============================================================================
# Menu items
# =============================================================================


class MenuItemsSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.menu_items_api"

    def view_replacement(self):
        return extend_schema(
            methods=["GET"],
            tags=["Menu"],
            operation_id="MenuItem_List",
            summary="List Menu Items",
            responses={
                200: MenuItemPayloadSerializer(many=True),
                401: ErrorResponseSerializer,
                403: ErrorResponseSerializer,
                404: ErrorResponseSerializer,
            },
        )(
            extend_schema(
                methods=["POST"],
                tags=["Menu"],
                operation_id="MenuItem_Create",
                summary="Create Menu Item",
                request=MenuItemCreateRequestSerializer,
                responses={
                    201: MenuItemCreateResponseSerializer,
                    400: ErrorResponseSerializer,
                    401: ErrorResponseSerializer,
                    403: ErrorResponseSerializer,
                    404: ErrorResponseSerializer,
                    500: ErrorResponseSerializer,
                },
            )(self.target_class)
        )


class MenuItemDetailSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.menu_item_detail_api"

    def view_replacement(self):
        return extend_schema(
            methods=["PATCH"],
            tags=["Menu"],
            operation_id="MenuItem_Update",
            summary="Update Menu Item",
            request=MenuItemUpdateRequestSerializer,
            responses={
                200: MenuItemPayloadSerializer,
                401: ErrorResponseSerializer,
                404: ErrorResponseSerializer,
            },
            parameters=[
                OpenApiParameter(
                    name="id",
                    type=OpenApiTypes.INT,
                    location=OpenApiParameter.PATH,
                    required=True,
                    description="Menu item primary key.",
                )
            ],
        )(
            extend_schema(
                methods=["DELETE"],
                tags=["Menu"],
                operation_id="MenuItem_Delete",
                summary="Delete Menu Item",
                responses={
                    200: CategorySuccessResponseSerializer,
                    401: ErrorResponseSerializer,
                    404: ErrorResponseSerializer,
                },
                parameters=[
                    OpenApiParameter(
                        name="id",
                        type=OpenApiTypes.INT,
                        location=OpenApiParameter.PATH,
                        required=True,
                        description="Menu item primary key.",
                    )
                ],
            )(self.target_class)
        )


# =============================================================================
# Public order and table APIs
# =============================================================================


class PublicOrderDetailSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.public_order_detail"

    def view_replacement(self):
        return extend_schema(
            tags=["Orders"],
            operation_id="Order_PublicDetail",
            summary="Public Order Detail",
            responses={
                200: PublicOrderDetailResponseSerializer,
                404: ErrorResponseSerializer,
            },
            parameters=[
                OpenApiParameter(
                    name="pk",
                    type=OpenApiTypes.INT,
                    location=OpenApiParameter.PATH,
                    required=True,
                    description="Order primary key.",
                )
            ],
        )(self.target_class)


class CreateTableSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.create_table_api"

    def view_replacement(self):
        return extend_schema(
            methods=["GET"],
            tags=["Tables"],
            operation_id="Table_List",
            summary="List Tables",
            responses={
                200: TablePayloadSerializer(many=True),
                401: ErrorResponseSerializer,
                404: ErrorResponseSerializer,
            },
        )(
            extend_schema(
                methods=["POST"],
                tags=["Tables"],
                operation_id="Table_Create",
                summary="Create Table",
                request=TableCreateRequestSerializer,
                responses={
                    201: TableCreateResponseSerializer,
                    400: ErrorResponseSerializer,
                    401: ErrorResponseSerializer,
                    403: ErrorResponseSerializer,
                    404: ErrorResponseSerializer,
                },
            )(self.target_class)
        )


class DeleteTableSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.delete_table_api"

    def view_replacement(self):
        return extend_schema(
            tags=["Tables"],
            operation_id="Table_Delete",
            summary="Delete Table",
            responses={
                200: CategorySuccessResponseSerializer,
                401: ErrorResponseSerializer,
                404: ErrorResponseSerializer,
            },
            parameters=[
                OpenApiParameter(
                    name="table_id",
                    type=OpenApiTypes.INT,
                    location=OpenApiParameter.PATH,
                    required=True,
                    description="Table primary key.",
                )
            ],
        )(self.target_class)


# =============================================================================
# Restaurant profile
# =============================================================================


class RestaurantProfileSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.restaurant_profile"

    def view_replacement(self):
        return extend_schema(
            methods=["GET"],
            tags=["Restaurant"],
            operation_id="Restaurant_Profile",
            summary="Get Restaurant Profile",
            responses={
                200: RestaurantProfileResponseSerializer,
                401: ErrorResponseSerializer,
            },
        )(
            extend_schema(
                methods=["POST"],
                tags=["Restaurant"],
                operation_id="Restaurant_ProfileCreate",
                summary="Create Restaurant Profile",
                request=RestaurantProfileRequestSerializer,
                responses={
                    200: RestaurantProfileSaveResponseSerializer,
                    400: ErrorResponseSerializer,
                    401: ErrorResponseSerializer,
                    500: ErrorResponseSerializer,
                },
            )(
                extend_schema(
                    methods=["PUT"],
                    tags=["Restaurant"],
                    operation_id="Restaurant_ProfileUpdate",
                    summary="Update Restaurant Profile",
                    request=RestaurantProfileRequestSerializer,
                    responses={
                        200: RestaurantProfileSaveResponseSerializer,
                        401: ErrorResponseSerializer,
                        500: ErrorResponseSerializer,
                    },
                )(self.target_class)
            )
        )


# =============================================================================
# AI endpoints
# =============================================================================


class AIImageSearchSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.ai_image_search"

    def view_replacement(self):
        return extend_schema(
            tags=["AI Import"],
            operation_id="AI_ImageSearch",
            summary="Search Food Image",
            description="Search Pexels for a food image using the supplied query.",
            parameters=[
                OpenApiParameter(
                    name="q",
                    type=OpenApiTypes.STR,
                    location=OpenApiParameter.QUERY,
                    required=False,
                    description="Food image search query.",
                )
            ],
            responses={
                200: AIImageSearchResponseSerializer,
            },
        )(self.target_class)


class AIMenuExtractSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.ai_menu_extract"

    def view_replacement(self):
        return extend_schema(
            tags=["AI Import"],
            operation_id="AI_MenuExtract",
            summary="Extract Menu From Image/PDF",
            description="Upload a restaurant menu file and extract structured menu items using Gemini Vision.",
            request=AIMenuExtractRequestSerializer,
            responses={
                200: AIMenuExtractResponseSerializer,
                401: ErrorResponseSerializer,
                500: AIMenuExtractResponseSerializer,
            },
        )(self.target_class)


# =============================================================================
# Logout (explicitly re-annotated because the existing decorator is not being
# picked up reliably in the current generated schema).
# =============================================================================


class LogoutSchemaExtension(OpenApiViewExtension):
    target_class = "restaurant.views.views.api_logout"

    def view_replacement(self):
        return extend_schema(
            tags=["Authentication"],
            operation_id="auth_logout",
            summary="Logout",
            description="Logout the authenticated user. The JWT token is stateless and should be discarded by the client.",
            responses={
                200: {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {"type": "string"},
                    },
                    "required": ["success", "message"],
                },
                401: ErrorResponseSerializer,
            },
        )(self.target_class)
