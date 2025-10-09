# restaurant/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views

from .views import (
    dashboard,
    menu_view,
    place_order,
    kitchen_interface,
    signup_view,
    CustomLogoutView,
    cancel_order,
    CategoryCreateView,
    FoodItemUpdateView,
    FoodItemDeleteView,
    order_confirmation,
    complete_order,
    download_qr_code,
    FoodItemCreateView,
    TableCreateView,
    cart_summary,
    delete_order_item_ajax,
    confirm_order_ajax,
    create_table_qr_view,
    create_restaurant,
    product_detail_html,
    menu_preview,
    product_json,
    add_to_cart_ajax,
    place_cart_order,
    product_detail_view,
    add_to_order,
    orders_json,
)

urlpatterns = [
    # Dashboard / management
    path('dashboard/', dashboard, name='dashboard'),
    path('manage-menu/', dashboard, name='manage_menu'),
    path('menu-preview/', menu_preview, name='menu_preview'),

    # Menu (public facing)
    path('menu/<int:restaurant_id>/<int:table_id>/', menu_view, name='menu_view'),
    path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/', product_detail_view, name='product_detail'),
    path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/html/', product_detail_html, name='product_detail_html'),
    path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/json/', product_json, name='product_json'),

    # Cart / order endpoints for the menu
    path('menu/<int:restaurant_id>/<int:table_id>/cart/add/<int:pk>/', add_to_cart_ajax, name='add_to_cart_ajax'),
    path('menu/<int:restaurant_id>/<int:table_id>/cart/summary/', cart_summary, name='cart_summary'),
    path('menu/<int:restaurant_id>/<int:table_id>/cart/place/', place_cart_order, name='place_cart_order'),

    # Quick add from menu (legacy / form)
    path('menu/<int:restaurant_id>/<int:table_id>/add/<int:pk>/', add_to_order, name='add_to_order'),

    # Place-order (form-based page)
    path('place_order/<int:table_id>/', place_order, name='place_order'),

    # Kitchen / admin
    path('kitchen/', kitchen_interface, name='kitchen_interface'),
    path('kitchen/orders/json/', orders_json, name='orders_json'),
    path('complete_order/<int:order_id>/', complete_order, name='complete_order'),

    # Order confirmation + item actions
    path('order_confirmation/<int:order_id>/', order_confirmation, name='order_confirmation'),
    path('order-item/<int:order_item_id>/delete/', delete_order_item_ajax, name='delete_order_item_ajax'),
    path('order/<int:order_id>/confirm/ajax/', confirm_order_ajax, name='confirm_order_ajax'),

    # QR / tables / restaurant creation
    path("download_qr/<int:table_id>/", download_qr_code, name="download_qr"),
    path('create-restaurant/', create_restaurant, name='create_restaurant'),
    path('table/new/', TableCreateView.as_view(), name='table_create'),
    path('tables/', create_table_qr_view, name='create_table_qr'),

    # FoodItem CRUD
    path('fooditem/new/', FoodItemCreateView.as_view(), name='fooditem_create'),
    path('menu/edit/<int:pk>/', FoodItemUpdateView.as_view(), name='edit_fooditem'),
    path('menu/delete/<int:pk>/', FoodItemDeleteView.as_view(), name='delete_fooditem'),

    # Category CRUD
    path('category/new/', CategoryCreateView.as_view(), name='category_create'),

    # Cancel order (non-AJAX fallback)
    path('cancel_order/<int:order_id>/', cancel_order, name='cancel_order'),

    # Auth (login/signup/logout)
    path('accounts/signup/', signup_view, name='signup'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='restaurant/login.html'), name='login'),
    path('', auth_views.LoginView.as_view(template_name='restaurant/login.html'), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
]
