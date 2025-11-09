from django.urls import path
from . import views

app_name = 'projetos'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard_projetos, name='dashboard'),

    # CRUD Projeto
    path('', views.projeto_list, name='projeto_list'),
    path('novo/', views.projeto_create, name='projeto_create'),
    path('<int:pk>/', views.projeto_detail, name='projeto_detail'),
    path('<int:pk>/editar/', views.projeto_edit, name='projeto_edit'),
    path('<int:pk>/excluir/', views.projeto_delete, name='projeto_delete'),

    # Participações
    path('<int:pk>/participacoes/servidores/', views.participacao_servidor_edit, name='participacao_servidor_edit'),
    path('<int:pk>/participacoes/estudantes/', views.participacao_estudante_edit, name='participacao_estudante_edit'),

    # Relatórios
    path('<int:pk>/relatorio/entregue/', views.relatorio_entregue, name='relatorio_entregue'),
    path('<int:pk>/relatorio/definir-proximo/', views.definir_proximo_relatorio, name='definir_proximo_relatorio'),

    # API
    path('api/horas-servidor/', views.api_horas_servidor, name='api_horas_servidor'),
]