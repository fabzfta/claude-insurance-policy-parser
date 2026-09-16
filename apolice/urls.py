from django.urls import path

from . import views

app_name = "apolice"

urlpatterns = [
    path("", views.escolher_tipo_operacao, name="escolher_tipo_operacao"),
    path("novo/upload/", views.upload_novo, name="upload_novo"),
    #path("renovacao/upload/", views.upload_renovacao, name="upload_renovacao"),
]