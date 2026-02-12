from django.urls import path
from . import views

app_name = 'refeitorio'

urlpatterns = [
    # Kiosk (público)
    path('checkin/', views.checkin_screen, name='checkin_screen'),
    path('validar/', views.validar_checkin, name='validar_checkin'),

    # Administrativo (requer login)
    path('dashboard/', views.dashboard, name='dashboard'),
    path('relatorio/', views.relatorio_periodo, name='relatorio'),
    path('bloqueios/', views.gerenciar_bloqueios, name='bloqueios'),

    # API
    path('api/stats/', views.api_estatisticas_hoje, name='api_stats'),
    path('api/ultimos-acessos/', views.api_ultimos_acessos_kiosk, name='api_ultimos_acessos'),

    #CSV
    path('exportar-csv/', views.exportar_csv, name='exportar_csv'),
]