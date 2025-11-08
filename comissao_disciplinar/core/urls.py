from django.urls import path, include
from core import views
from django.contrib.auth import views as auth_views

app_name = 'core'  # Esta linha é crucial

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Novas páginas do dashboard
    path('comissao/', views.comissao_dashboard, name='comissao_dashboard'),
    path('processos/', views.processos_list, name='processos_list'),
    path('relatorios/', views.relatorios_estatisticas, name='relatorios_estatisticas'),
    path('configuracoes/', views.configuracoes_sistema, name='configuracoes_sistema'),

    # Ocorrências (mantenha as existentes)
    path('ocorrencias/', views.ocorrencia_list, name='ocorrencia_list'),
    path('ocorrencias/nova/', views.ocorrencia_create, name='ocorrencia_create'),
    path('ocorrencias/rapida/', views.ocorrencia_rapida_create, name='ocorrencia_rapida_create'),
    path('ocorrencias/<int:pk>/', views.ocorrencia_detail, name='ocorrencia_detail'),

    # Ações (mantenha as existentes)
    path('ocorrencias/<int:pk>/analise/', views.ocorrencia_iniciar_analise, name='ocorrencia_iniciar_analise'),
    path('ocorrencias/<int:pk>/notificar/', views.ocorrencia_notificar, name='ocorrencia_notificar'),
    path('ocorrencias/<int:pk>/defesa/', views.ocorrencia_apresentar_defesa, name='ocorrencia_apresentar_defesa'),
    path('ocorrencias/<int:pk>/sancao/', views.ocorrencia_aplicar_sancao, name='ocorrencia_aplicar_sancao'),
    path('ocorrencias/<int:pk>/comissao/', views.comissao_create, name='comissao_create'),
    path('ocorrencias/<int:pk>/documento/<str:tipo>/', views.gerar_documento, name='gerar_documento'),

    # Relatórios
    path('estudantes/<str:matricula>/relatorio/', views.relatorio_estudante, name='relatorio_estudante'),
    path('estudantes/<str:matricula>/', views.estudante_detail, name='estudante_detail'),
    #path('estudantes/<str:matricula>/editar/', views.estudante_edit, name='estudante_edit'),

    # Auth com recuperação de senha
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Notificações (mantenha as existentes)
    path('notificacoes/', views.notificacoes_list, name='notificacoes_list'),
    path('notificacoes/<int:pk>/marcar-lida/', views.notificacao_marcar_lida, name='notificacao_marcar_lida'),
    path('notificacoes/marcar-todas-lidas/', views.notificacao_marcar_todas_lidas, name='notificacao_marcar_todas_lidas'),
    path('preferencias/notificacoes/', views.preferencias_notificacao, name='preferencias_notificacao'),
    path('api/notificacoes/nao-lidas/', views.api_notificacoes_nao_lidas, name='api_notificacoes_nao_lidas'),
    path('api/notificacoes/recentes/', views.api_notificacoes_recentes, name='api_notificacoes_recentes'),
    path('guia-regulamento-discente/', views.guia_regulamento_discente, name='guia_regulamento_discente'),
    path('meu-perfil/', views.meu_perfil, name='meu_perfil'),
    path('diagnostico-email/', views.diagnostico_email, name='diagnostico_email'),
    path('testar-email/', views.testar_email, name='testar_email'),
    path('api/estudantes/filtrar/', views.api_filtrar_estudantes, name='api_filtrar_estudantes'),
    path('api/servidores/filtrar/', views.api_filtrar_servidores, name='api_filtrar_servidores'),
]