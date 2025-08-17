
from django.urls import path
from . import views

urlpatterns = [
    path('', views.location_selector, name='select_location'),
    # path('get-kabupatens/', views.get_kabupatens, name='get_kabupatens'),
    path('validate-link-excel/', views.validate_link_excel, name='validate_link_excel'),
    path("download-error-excel/", views.download_error_excel, name="download_error_excel"),
    path("download-template-excel/", views.download_template_excel, name="download_template_excel"),
    path('validate-map-txt/', views.validate_map_txt, name='validate_map_txt'),
]
