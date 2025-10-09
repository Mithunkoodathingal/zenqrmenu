# restaurant/urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from .views import (
    dashboard,
    menu_view,
    kitchen_interface,
    signup_view,
    login_view,
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
    orders_json,
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
    product_detail,
    manage_menu,
)

urlpatterns = [
    # Auth
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Dashboard / menu management
    path('dashboard/', dashboard, name='dashboard'),
    path('manage-menu/', manage_menu, name='manage_menu'),
    path('menu-preview/', menu_preview, name='menu_preview'),

    # Public menu
    path('menu/<int:restaurant_id>/<int:table_id>/', menu_view, name='menu_view'),
    path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/', product_detail_view, name='product_detail'),
    path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/html/', product_detail_html, name='product_detail_html'),
    path('menu/<int:restaurant_id>/<int:table_id>/item/<int:pk>/json/', product_json, name='product_json'),
    path('menu/<int:restaurant_id>/<int:table_id>/add/<int:pk>/', add_to_order, name='add_to_order'),

    # Cart / ajax
    path('menu/<int:restaurant_id>/<int:table_id>/cart/add/<int:pk>/', add_to_cart_ajax, name='add_to_cart_ajax'),
    path('menu/<int:restaurant_id>/<int:table_id>/cart/place/', place_cart_order, name='place_cart_order'),
    path('menu/<int:restaurant_id>/<int:table_id>/cart/summary/', cart_summary, name='cart_summary'),

    # Orders
    path('order_confirmation/<int:order_id>/', order_confirmation, name='order_confirmation'),
    path('cancel_order/<int:order_id>/', cancel_order, name='cancel_order'),
    path('order/item/<int:order_item_id>/delete/', delete_order_item_ajax, name='delete_order_item_ajax'),
    path('order/<int:order_id>/confirm/', confirm_order_ajax, name='confirm_order_ajax'),
    path('complete_order/<int:order_id>/', complete_order, name='complete_order'),

    # Kitchen / polling
    path('kitchen/', kitchen_interface, name='kitchen_interface'),
    path('kitchen/orders/json/', orders_json, name='orders_json'),

    # CRUD endpoints
    path('category/new/', CategoryCreateView.as_view(), name='category_create'),
    path('fooditem/new/', FoodItemCreateView.as_view(), name='fooditem_create'),
    path('menu/edit/<int:pk>/', FoodItemUpdateView.as_view(), name='edit_fooditem'),
    path('menu/delete/<int:pk>/', FoodItemDeleteView.as_view(), name='delete_fooditem'),

    # Tables / QR / restaurant create
    path('table/new/', TableCreateView.as_view(), name='table_create'),
    path('tables/', create_table_qr_view, name='create_table_qr'),
    path('create-restaurant/', create_restaurant, name='create_restaurant'),
    path('download_qr/<int:table_id>/', download_qr_code, name='download_qr'),

    # Password reset using Django built-in class-based views.
    # Templates should be placed under "registration/" (see templates below).
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            success_url = reverse_lazy('password_reset_done')
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

    # allauth - social login endpoints (Google, Facebook)
    path('accounts/', include('allauth.urls')),
]
