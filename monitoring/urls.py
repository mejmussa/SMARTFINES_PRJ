from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/add/', views.vehicle_add, name='vehicle_add'),
    path('vehicles/edit/<int:pk>/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicles/delete/<int:pk>/', views.vehicle_delete, name='vehicle_delete'),
    path('pending/', views.pending_offenses, name='pending_offenses'),
    path('paid/', views.paid_offenses, name='paid_offenses'),
    path('penalty/', views.penalty_offenses, name='penalty_offenses'),
    path('balance/', views.balance_history, name='balance_history'),
    path('balance/deposit/', views.deposit, name='deposit'),
]