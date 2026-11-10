from django.urls import path

from . import views

urlpatterns = [
    path("menu/api/inventory/ingredients/", views.IngredientList.as_view()),
    path("menu/api/inventory/ingredients/<int:pk>/", views.IngredientDetail.as_view()),
    path("menu/api/inventory/ingredients/<int:pk>/adjust/", views.adjust_stock),
    path("menu/api/inventory/ingredients/<int:pk>/purchase/", views.record_purchase),
    path("menu/api/inventory/history/", views.history),
    path("menu/api/inventory/purchases/", views.purchases),
    path("menu/api/inventory/reservations/", views.reservations),
    path("api/recipes/", views.recipe_list),
    path("api/recipes/<int:food_item_id>/", views.recipe_detail),
]
