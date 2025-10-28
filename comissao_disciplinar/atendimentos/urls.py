# atendimentos/urls.py

from django.urls import path
from . import views

app_name = 'atendimentos'

urlpatterns = [
    path('', views.atendimento_list, name='atendimento_list'),
    path('novo/', views.atendimento_create, name='atendimento_create'),
    path('<int:pk>/', views.atendimento_detail, name='atendimento_detail'),
    #path('<int:pk>/editar/', views.atendimento_edit, name='atendimento_edit'),
    path('estudante/<str:matricula>/', views.atendimentos_por_estudante, name='atendimentos_estudante'),
    #path('relatorio/', views.atendimento_relatorio, name='atendimento_relatorio'),
]
