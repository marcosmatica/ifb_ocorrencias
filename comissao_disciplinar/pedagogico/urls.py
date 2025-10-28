# pedagogico/urls.py

from django.urls import path
from . import views

app_name = 'pedagogico'

urlpatterns = [
    # Disciplinas
    path('disciplinas/', views.disciplina_list, name='disciplina_list'),
    path('disciplinas/nova/', views.disciplina_create, name='disciplina_create'),
    #path('disciplinas/<int:pk>/', views.disciplina_detail, name='disciplina_detail'),

    # Conselho de Classe
    path('conselhos/', views.conselho_list, name='conselho_list'),
    path('conselhos/novo/', views.conselho_create, name='conselho_create'),
    path('conselhos/<int:pk>/', views.conselho_detail, name='conselho_detail'),
    path('conselhos/<int:conselho_pk>/estudante/<int:estudante_id>/', views.conselho_estudante_edit,
         name='conselho_estudante_edit'),

    # Ficha do Aluno
    path('ficha-aluno/<str:matricula>/', views.ficha_aluno, name='ficha_aluno'),
]
