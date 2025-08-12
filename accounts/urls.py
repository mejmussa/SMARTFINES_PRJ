from django.urls import path
from . import views


urlpatterns = [
    path('update-guest-timezone/', views.update_guest_timezone, name='update_guest_timezone'),
    path('manage-superuser/', views.grant_superuser_view, name='grant-superuser'),
]



