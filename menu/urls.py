from django.urls import path

from . import views

urlpatterns = [
    path("menu/api/categories/", views.CategoryList.as_view()),
    path("menu/api/categories/<int:pk>/", views.CategoryDetail.as_view()),
    path("menu/api/items/", views.ItemList.as_view()),
    path("menu/api/items/<int:pk>/", views.ItemDetail.as_view()),
    path("api/branches/<int:pk>/menu-overrides/", views.ItemOverrides.as_view()),
    path("api/branches/<int:pk>/category-overrides/", views.CategoryOverrides.as_view()),
    path("menu/api/table/<int:pk>/", views.public_table_menu),
    path("api/ai-import/extract/", views.ai_extract),
    path("api/ai-import/image-search/", views.ai_image_search),
    path("menu/api/search/", views.search),
]
