# restaurant/urls.py
from django.urls import path
from .views import (
    dashboard, menu_view, place_order, kitchen_interface, signup_view, CustomLogoutView, cancel_order, 
    CategoryCreateView, FoodItemUpdateView, FoodItemDeleteView, order_confirmation, complete_order,download_qr_code, 
    FoodItemCreateView, TableCreateView,create_table_qr_view, create_restaurant, menu_preview, product_json, add_to_cart_ajax, place_cart_order, product_detail_view, add_to_order
)
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('manage-menu/', dashboard, name='manage_menu'),
    path('menu-preview/', menu_preview, name='menu_preview'),
    path('menu/<int:restaurant_id>/<int:table_id>/', menu_view, name='menu_view'),
    path('menu/<int:restaurant_id>/<int:table_id>/', menu_view, name='menu_view'),
    path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/', product_detail_view, name='product_detail'),  # ✅ detail
    path('menu/<int:restaurant_id>/<int:table_id>/add/<int:pk>/', add_to_order, name='add_to_order'),      # ✅ add-to-order
    path('place_order/<int:table_id>/', place_order, name='place_order'),
    path('kitchen/', kitchen_interface, name='kitchen_interface'),
    path("download_qr/<int:table_id>/", download_qr_code, name="download_qr"),
    # CRUD Views
    path('cancel_order/<int:order_id>/', cancel_order, name='cancel_order'),
    path('category/new/', CategoryCreateView.as_view(), name='category_create'),
    path('fooditem/new/', FoodItemCreateView.as_view(), name='fooditem_create'),
    path('table/new/', TableCreateView.as_view(), name='table_create'),
    path('tables/', create_table_qr_view, name='create_table_qr'),
    path('complete_order/<int:order_id>/', complete_order, name='complete_order'),
    
    path('create-restaurant/', create_restaurant, name='create_restaurant'),
    path('accounts/signup/', signup_view, name='signup'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='restaurant/login.html'), name='login'),
    path('', auth_views.LoginView.as_view(template_name='restaurant/login.html'), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('menu/edit/<int:pk>/', FoodItemUpdateView.as_view(), name='edit_fooditem'),
    path('menu/delete/<int:pk>/', FoodItemDeleteView.as_view(), name='delete_fooditem'),
    path('order_confirmation/<int:order_id>/', order_confirmation, name='order_confirmation'),
     path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/json/', product_json, name='product_json'),
    path('menu/<int:restaurant_id>/<int:table_id>/cart/add/<int:pk>/', add_to_cart_ajax, name='add_to_cart_ajax'),
    path('menu/<int:restaurant_id>/<int:table_id>/cart/place/', place_cart_order, name='place_cart_order'),

]