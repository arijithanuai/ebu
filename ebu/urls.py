
from django.urls import path
from . import testView, views

urlpatterns = [
    path('', views.location_selector, name='select_location'), #with token view
    path('validate/',testView.location_selector,name='select_location_token'), #without token view
    path('get-kabupatens/', views.get_kabupatens, name='get_kabupatens'),
    path('validate-link-excel/', views.validate_link_excel, name='validate_link_excel'),
    path("download-error-excel/", views.download_error_excel, name="download_error_excel"),
    path("download-template-excel/", views.download_template_excel, name="download_template_excel"),
    path('validate-map-txt/', views.validate_map_txt, name='validate_map_txt'),
    path('validate-db-file/', views.validate_db_file, name='validate_db_file'),
    path('done/',views.data_updated,name='done')
    # path('upload-db-file/',views.upload_db_file, name="upload_db_file")
]
