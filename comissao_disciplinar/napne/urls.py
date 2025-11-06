from django.urls import path
from . import views

app_name = 'napne'

urlpatterns = [
    # Dashboard
    path('', views.napne_dashboard, name='dashboard'),
    
    # Fichas NAPNE
    path('fichas/', views.ficha_napne_list, name='ficha_list'),
    path('fichas/nova/', views.ficha_napne_create, name='ficha_create'),
    path('fichas/<int:pk>/', views.ficha_napne_detail, name='ficha_detail'),
    path('fichas/<int:pk>/editar/', views.ficha_napne_edit, name='ficha_edit'),
    
    # Atendimentos NAPNE
    path('atendimentos/', views.atendimento_napne_list, name='atendimento_list'),
    path('atendimentos/novo/', views.atendimento_napne_create, name='atendimento_create'),
    path('atendimentos/<int:pk>/', views.atendimento_napne_detail, name='atendimento_detail'),
    path('atendimentos/<int:pk>/editar/', views.atendimento_napne_edit, name='atendimento_edit'),
    
    # Encaminhamentos
    path('atendimentos/<int:atendimento_pk>/encaminhamento/', views.adicionar_encaminhamento, name='adicionar_encaminhamento'),
    
    # API
    path('api/estudantes/', views.api_buscar_estudantes_napne, name='api_estudantes'),
]