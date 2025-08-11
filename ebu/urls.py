
from django.urls import path
from . import views

urlpatterns = [
    path('', views.location_selector, name='select_location'),
    path('get-kabupatens/', views.get_kabupatens, name='get_kabupatens'),
    path('validate-link-excel/', views.validate_link_excel, name='validate_link_excel'),
    path('save-link-excel/', views.save_link_excel, name='save_link_excel'),
]
