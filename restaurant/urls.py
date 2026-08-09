
# restaurant/urls.py

# -------------------------------------------------------------------------------

from django.urls import path, include

from django.contrib.auth import views as auth_views

from django.urls import reverse_lazy

from django.conf import settings

from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter

# -----------------------------------------------------------------------------
# KDS Views
# -----------------------------------------------------------------------------

from restaurant.views.attendance import StaffAttendanceAPIView, StaffAttendanceUpdateAPIView, StaffClockInAPIView, StaffClockOutAPIView
from restaurant.views.audit import AuditLogAPIView
from restaurant.views.breaks import StaffBreakAPIView, StaffBreakEndAPIView, StaffBreakStartAPIView
from restaurant.views.kds import KDSNotesAPIView, KDSOrdersAPIView, KDSPriorityAPIView, KDSStatisticsAPIView, KDSStatusAPIView

# -----------------------------------------------------------------------------
# Staff Views
# -----------------------------------------------------------------------------

from restaurant.views.kitchen_notes import KitchenNoteAPIView, KitchenNotesAPIView
from restaurant.views.staff import (

    StaffListAPIView,

    StaffCreateAPIView,

    StaffDetailAPIView,
    
    StaffShiftScheduleAPIView,

    StaffUpdateAPIView,

    StaffDeleteAPIView,

    StaffShiftAPIView,

    StaffRoleAPIView,

)

from . import debug_views

from .views.views import *

# from subscription.views import subscription_status


# ✅ DRF ROUTER (ALL API VIEWSETS HERE)
router = DefaultRouter()
# router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'orders', OrderViewSet, basename='orders')


urlpatterns = [









# -----------------------------------------------------------------------------
# ---------------------- \/ OLD AND UNUSED API PATHS \/ -----------------------
# -----------------------------------------------------------------------------


    # ================= AUTH =================
    # path('', login_view, name='login'),
    # path('signup/', signup_view, name='signup'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    # path('resend-confirmation/', resend_confirmation, name='resend_confirmation'),
    # path('resend-by-email/', resend_confirmation_by_email, name='resend_confirmation_by_email'),
    # path('terms-and-conditions/', terms_conditions, name='terms_conditions'),

    # ================= DASHBOARD =================
    # path('dashboard/', dashboard, name='dashboard'),
    # path('manage-menu/', manage_menu, name='manage_menu'),
    # path('menu-preview/', menu_preview, name='menu_preview'),
    # path('ajax/toggle-item-availability/', toggle_item_availability, name='toggle_item_availability'),

    # ================= PUBLIC MENU =================
    # path('menu/<int:restaurant_id>/<int:table_id>/', menu_view, name='menu_view'),
    # path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/', product_detail_view, name='product_detail'),
    # path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/html/', product_detail_html, name='product_detail_html'),
    # path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/json/', product_json, name='product_json'),
    # path('menu/<int:restaurant_id>/<int:table_id>/add/<int:pk>/', add_to_order, name='add_to_order'),

    # ================= CART =================
    # path('menu/<int:restaurant_id>/<int:table_id>/cart/add/<int:pk>/', add_to_cart_ajax, name='add_to_cart_ajax'),
    # path('menu/<int:restaurant_id>/<int:table_id>/cart/place/', place_cart_order, name='place_cart_order'),
    # path('menu/<int:restaurant_id>/<int:table_id>/cart/summary/', cart_summary, name='cart_summary'),

    # ================= ORDERS =================
    # path('order_confirmation/<int:order_id>/', order_confirmation, name='order_confirmation'),
    # path('cancel_order/<int:order_id>/', cancel_order, name='cancel_order'),
    # path('order/item/<int:order_item_id>/delete/', delete_order_item_ajax, name='delete_order_item_ajax'),
    # path('order/<int:order_id>/confirm/', confirm_order_ajax, name='confirm_order_ajax'),
    # path('complete_order/<int:order_id>/', complete_order, name='complete_order'),
    # path('orders/completed/', completed_orders, name='completed_orders'),

    # ================= KITCHEN =================
    # path('kitchen/', kitchen_interface, name='kitchen_interface'),
    # path('kitchen/orders/json/', orders_json, name='orders_json'),

    # ================= CRUD =================
    # path('category/new/', CategoryCreateView.as_view(), name='category_create'),
    # path('fooditem/new/', FoodItemCreateView.as_view(), name='fooditem_create'),
    # path('menu/edit/<int:pk>/', FoodItemUpdateView.as_view(), name='edit_fooditem'),
    # path('menu/delete/<int:pk>/', FoodItemDeleteView.as_view(), name='delete_fooditem'),

    # ================= TABLE / QR =================
    # path('table/new/', TableCreateView.as_view(), name='table_create'),
    # path('tables/', create_table_qr_view, name='create_table_qr'),
    # path('create-restaurant/', create_restaurant, name='create_restaurant'),
    # path('download_qr/<int:table_id>/', download_qr_code, name='download_qr'),
    
    
    
# -----------------------------------------------------------------------------
# ---------------------- ^ OLD AND UNUSED API PATHS ^ -------------------------
# -----------------------------------------------------------------------------
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
# -----------------------------------------------------------------------------
# ============================== NEW IMPORTANT ================================
# -----------------------------------------------------------------------------
    
    path('menu/api/', include(router.urls)),
    
    
    
# -----------------------------------------------------------------------------
#                           Restaurant Create API
# -----------------------------------------------------------------------------
    
    path(
        "restaurants/",
        RestaurantCreateAPIView.as_view(),
        name="restaurant-create",
    ),
    
    path(
        "restaurants/<int:pk>/",
        RestaurantDetailAPIView.as_view(),
        name="restaurant-detail",
    ),
    
    path(
    "my/",
        MyRestaurantAPIView.as_view(),
        name="my-restaurant",
    ),
    
    # path(
    #     "<int:restaurant_id>/",
    #     RestaurantDetailAPIView.as_view(),
    #     name="restaurant-detail",
    # ),
    
    path(
        "<int:restaurant_id>/update/",
        UpdateRestaurantAPIView.as_view(),
        name="restaurant-update",
    ),
    
    path(
        "<int:restaurant_id>/delete/",
        DeleteRestaurantAPIView.as_view(),
        name="restaurant-delete",
    ),
    
# =============================================================================
# Nearby Restaurants
# =============================================================================

    path(

        "nearby/",

        NearbyRestaurantAPIView.as_view(),

        name="nearby-restaurants",

    ),
    
# =============================================================================
# Restaurant List
# =============================================================================

    path(

        "",

        RestaurantListAPIView.as_view(),

        name="restaurant-list",

    ),
    
# -----------------------------------------------------------------------------
#                           Password RESET
# -----------------------------------------------------------------------------

    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        success_url=reverse_lazy('password_reset_done')
    ), name='password_reset'),

    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),

    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')
    ), name='password_reset_confirm'),

    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    path("__debug/diagnostic/", debug_views.diagnostic, name="diagnostic"),
    # path('test-email/', test_email, name='test_email'),

# -----------------------------------------------------------------------------
# ---------------------- API's EXISTING ---------------------------------------
# -----------------------------------------------------------------------------

    path('menu/api/categories/', categories_api),
    
    path('menu/api/categories/<int:id>/', category_detail_api),

    path("menu/api/restaurant/", restaurant_profile),
    
    # path("menu/api/public/<int:restaurant_id>/", public_menu),

    path('menu/api/items/', menu_items_api),
    
    path('menu/api/items/<int:id>/', menu_item_detail_api),
    
    path('menu/api/orders/<int:pk>/public/',public_order_detail, name='public-order-detail'),

    path('menu/api/tables/', create_table_api),
    
    path('menu/api/tables/<int:table_id>/', delete_table_api),
    
# -----------------------------------------------------------------------------
#                           EMail / Password
# -----------------------------------------------------------------------------

    path("api/resend-verification/", resend_verification),
    
    path("api/password/reset/", password_reset),
    
    path("api/auth/password/reset/", password_reset),
    
    path("api/password/reset/confirm/", password_reset_confirm),
    
    path("api/auth/password/reset/confirm/", password_reset_confirm),

# -----------------------------------------------------------------------------
#                               JWT API's
# -----------------------------------------------------------------------------

    path('api/auth/login/', api_login),
    
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    
    path('api/auth/logout/', api_logout),
    
    path('api/register/', api_register),
    
    path('api/login/', api_login),
    
    path('api/user/', api_user),
    
    path('api/logout/', api_logout),
    
    path('api/auth/user/', user_detail_api),
    
    path("api/auth/google/", google_login),
    
# -----------------------------------------------------------------------------
#               Subscription Status api(From Subscription app)
# -----------------------------------------------------------------------------

    # path('menu/api/subscription/', subscription_status),

# -----------------------------------------------------------------------------
#                               Menu URL's
# -----------------------------------------------------------------------------

    path('menu/table/<int:table_id>/', menu_view_by_table, name='menu_by_table'),
    
    path('menu/api/table/<int:table_id>/', public_menu_by_table),

# -----------------------------------------------------------------------------
#                       AI Menu Creation API's
# -----------------------------------------------------------------------------

    path( "api/ai-import/extract/", ai_menu_extract ),
    
    path( "api/ai-import/image-search/", ai_image_search),
    
# =============================================================================
#                          Staff List / Create
# =============================================================================

    path(

        "api/staff/",

        StaffListAPIView.as_view(),

        name="staff-list",

    ),

    path(

        "api/staff/create/",

        StaffCreateAPIView.as_view(),

        name="staff-create",

    ),

    # ----------------------------------------------------------
    # Staff Detail
    # ----------------------------------------------------------

    path(

        "api/staff/<int:pk>/",

        StaffDetailAPIView.as_view(),

        name="staff-detail",

    ),

    # ----------------------------------------------------------
    # Staff Update
    # ----------------------------------------------------------

    path(

        "api/staff/<int:pk>/update/",

        StaffUpdateAPIView.as_view(),

        name="staff-update",

    ),

    # ----------------------------------------------------------
    # Staff Delete
    # ----------------------------------------------------------

    path(

        "api/staff/<int:pk>/delete/",

        StaffDeleteAPIView.as_view(),

        name="staff-delete",

    ),

    # ----------------------------------------------------------
    # Staff Shift
    # ----------------------------------------------------------

    path(

        "api/staff/<int:pk>/shift/",

        StaffShiftAPIView.as_view(),

        name="staff-shift",

    ),

    # ----------------------------------------------------------
    # Staff Role
    # ----------------------------------------------------------

    path(

        "api/staff/<int:pk>/role/",

        StaffRoleAPIView.as_view(),

        name="staff-role",

    ),
    
    # ----------------------------------------------------------
    # Staff Shift Shedule
    # ----------------------------------------------------------
    
    path(

        "api/staff/<int:pk>/shift-schedule/",

        StaffShiftScheduleAPIView.as_view(),

        name="staff-shift-schedule",

    ),
    
    # ----------------------------------------------------------
    # Staff Role API
    # ----------------------------------------------------------
    
    # path(
        
    #     "staff/role/<int:staff_id>/",
        
    #     StaffRoleAPIView.as_view(),
        
    #     name="staff-role",
        
    # ),
    
# ==========================================================
#                       KDS URL's
# ==========================================================

    path(
        
        "kds/orders/",
        
        KDSOrdersAPIView.as_view(),
        
        name="kds-orders",
        
    ),

    path(
        
        "kds/orders/<int:order_id>/status/",
        
        KDSStatusAPIView.as_view(),
        
        name="kds-status",
        
    ),

    path(
        
        "kds/orders/<int:order_id>/priority/",
        
        KDSPriorityAPIView.as_view(),
        
        name="kds-priority",
        
    ),

    path(
        
        "kds/orders/<int:order_id>/notes/",
        
        KDSNotesAPIView.as_view(),
        
        name="kds-notes",
        
    ),

    path(
        
        "kds/statistics/",
        
        KDSStatisticsAPIView.as_view(),
        
        name="kds-statistics",
        
    ),
    
# ==========================================================
#                  ATTENDANCE API URL's
# ==========================================================
    
    path(
        
        "staff/attendance/",
        
        StaffAttendanceAPIView.as_view(),
        
        name="staff-attendance",
        
    ),

    path(
        
        "staff/attendance/clock-in/",
        
        StaffClockInAPIView.as_view(),
        
        name="staff-clock-in",
        
    ),

    path(
        
        "staff/attendance/clock-out/",
        
        StaffClockOutAPIView.as_view(),
        
        name="staff-clock-out",
        
    ),

    path(
        
        "staff/attendance/<int:attendance_id>/",
        
        StaffAttendanceUpdateAPIView.as_view(),
        
        name="staff-attendance-update",
        
    ),
    
# ==========================================================
#                 STAFF BREAKS API URL's
# ==========================================================
    
    path(
        
        "staff/break/start/",
        
        StaffBreakStartAPIView.as_view(),
        
        name="staff-break-start",
        
    ),

    path(
        
        "staff/break/end/",
        
        StaffBreakEndAPIView.as_view(),
        
        name="staff-break-end",
        
    ),

    path(
        
        "staff/breaks/",
        
        StaffBreakAPIView.as_view(),
        
        name="staff-breaks",
        
    ),
    
# ==========================================================
#                 KITCHEN NOTES API URL's
# ==========================================================
    
    path(
        
        "kitchen/notes/",
        
        KitchenNotesAPIView.as_view(),
        
        name="kitchen-notes",
        
    ),

    path(
        
        "kitchen/notes/<int:note_id>/",
        
        KitchenNoteAPIView.as_view(),
        
        name="kitchen-note",
        
    ),
    
# ==========================================================
#                  AUDIT LOG API URL's
# ==========================================================
    
    path(
        
        "audit/logs/",
        
        AuditLogAPIView.as_view(),
        
        name="audit-logs",
        
    ),
    
    
]

# ================= STATIC =================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



