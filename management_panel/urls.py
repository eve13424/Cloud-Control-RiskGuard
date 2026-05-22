# БЛОК ИМПОРТА МАРШРУТИЗАЦИИ
from django.urls import path  # path используется для задания URL-маршрутов приложения.
from . import views  # views содержит функции представлений веб-панели management_panel.


# БЛОК URL-МАРШРУТОВ ПРИЛОЖЕНИЯ
urlpatterns = [
    path("", views.index, name="index"),  # Главная страница панели управления контейнером безопасности.
    path("admin-console/", views.admin_console, name="admin_console"),  # Административная страница параметров контейнера.
    path("reset/", views.reset_demo, name="reset_demo"),  # Сброс и повторный запуск демонстрационного сценария.
]