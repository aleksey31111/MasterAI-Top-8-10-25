"""
URL-маршруты для приложения finances
"""
from django.urls import path
from . import views

urlpatterns = [
    # Главная страница - дашборд
    path('', views.dashboard, name='dashboard'),

    # Управление операциями
    path('add/', views.add_operation, name='add_operation'),
    path('list/', views.operation_list, name='operation_list'),
    path('delete/<int:operation_id>/', views.delete_operation, name='delete_operation'),

    # Статистика и поиск
    path('stats/', views.statistics, name='statistics'),
    path('search/', views.search_by_period, name='search'),
]
