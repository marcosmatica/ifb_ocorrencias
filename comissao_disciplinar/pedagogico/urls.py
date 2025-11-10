# pedagogico/urls.py

from django.urls import path
from . import views

app_name = 'pedagogico'

urlpatterns = [
    # Disciplinas
    path('disciplinas/', views.disciplina_list, name='disciplina_list'),
    path('disciplinas/nova/', views.disciplina_create, name='disciplina_create'),

    # Conselho de Classe - Gestão
    path('conselhos/', views.conselho_list, name='conselho_list'),
    path('conselhos/novo/', views.conselho_create, name='conselho_create'),
    path('conselhos/<int:pk>/', views.conselho_detail, name='conselho_detail'),
    path('conselhos/<int:pk>/fechar/', views.conselho_fechar, name='conselho_fechar'),
    path('conselhos/<int:pk>/reabrir/', views.conselho_reabrir, name='conselho_reabrir'),

    # Conselho - Painel Unificado
    path('conselhos/<int:pk>/painel/', views.conselho_painel, name='conselho_painel'),

    # Conselho - Docente
    path('conselhos/<int:pk>/assumir/<int:disciplina_turma_id>/',
         views.conselho_docente_assumir, name='conselho_docente_assumir'),
    path('conselhos/<int:pk>/preencher-turma/<int:disciplina_turma_id>/',
         views.conselho_docente_preencher_turma, name='conselho_docente_preencher_turma'),
    path('conselhos/<int:pk>/preencher-estudantes/<int:disciplina_turma_id>/',
         views.conselho_docente_preencher_estudantes, name='conselho_docente_preencher_estudantes'),

    # Conselho - Coordenação
    path('conselhos/<int:conselho_pk>/estudante/<int:estudante_id>/',
         views.conselho_estudante_edit, name='conselho_estudante_edit'),

    # Ficha do Aluno
    path('ficha-aluno/<str:matricula>/', views.ficha_aluno, name='ficha_aluno'),
]