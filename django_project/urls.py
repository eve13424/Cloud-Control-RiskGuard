# БЛОК ИМПОРТА МОДУЛЕЙ МАРШРУТИЗАЦИИ
from django.contrib import admin
from django.urls import path, include


# БЛОК URL-МАРШРУТОВ ПРОЕКТА
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("management_panel.urls")),
]