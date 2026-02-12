"""
Главный файл URL-маршрутов проекта
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('finances.urls')),  # Подключаем URL приложения finances
]
