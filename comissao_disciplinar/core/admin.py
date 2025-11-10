from django.contrib import admin
from .models import *


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ['nome', 'sigla', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome', 'sigla']


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'campus', 'codigo', 'ativo']
    list_filter = ['campus', 'ativo']
    search_fields = ['nome', 'codigo']


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'curso', 'ano', 'semestre', 'ativa']
    list_filter = ['ano', 'semestre', 'ativa', 'curso__campus']
    search_fields = ['nome']


@admin.register(Estudante)
class EstudanteAdmin(admin.ModelAdmin):
    list_display = ['matricula_sga', 'nome', 'turma', 'situacao']
    list_filter = ['situacao', 'campus', 'curso']
    search_fields = ['nome', 'matricula_sga', 'email']


@admin.register(Servidor)
class ServidorAdmin(admin.ModelAdmin):
    list_display = ['siape', 'nome', 'funcao', 'membro_comissao_disciplinar']
    list_filter = ['membro_comissao_disciplinar', 'campus']
    search_fields = ['nome', 'siape']


@admin.register(Infracao)
class InfracaoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'gravidade', 'ativo']
    list_filter = ['gravidade', 'ativo']
    search_fields = ['codigo', 'descricao']


@admin.register(Sancao)
class SancaoAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'descricao']
    filter_horizontal = ['infraccoes']


@admin.register(Ocorrencia)
class OcorrenciaAdmin(admin.ModelAdmin):
    list_display = ['id', 'data', 'status', 'curso', 'turma', 'responsavel_registro']
    list_filter = ['status', 'data', 'curso', 'infracao__gravidade']
    search_fields = ['descricao', 'estudantes__nome']
    date_hierarchy = 'data'


@admin.register(ComissaoProcessoDisciplinar)
class ComissaoAdmin(admin.ModelAdmin):
    list_display = ['ocorrencia', 'presidente', 'data_instauracao', 'data_conclusao']
    filter_horizontal = ['membros']


@admin.register(NotificacaoOficial)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ['ocorrencia', 'tipo', 'data_envio', 'meio_envio']
    list_filter = ['tipo', 'meio_envio']


@admin.register(Recurso)
class RecursoAdmin(admin.ModelAdmin):
    list_display = ['ocorrencia', 'data_protocolo', 'resultado', 'data_decisao']
    list_filter = ['resultado']


@admin.register(DocumentoGerado)
class DocumentoGeradoAdmin(admin.ModelAdmin):
    list_display = ['ocorrencia', 'tipo_documento', 'data_geracao', 'assinado']
    list_filter = ['tipo_documento', 'assinado']


@admin.register(OcorrenciaRapida)
class OcorrenciaRapidaAdmin(admin.ModelAdmin):
    list_display = ['id', 'data', 'horario', 'turma', 'tipo_rapido', 'responsavel_registro']
    list_filter = ['tipo_rapido', 'data', 'turma__curso__campus']
    search_fields = ['estudantes__nome', 'estudantes__matricula_sga', 'descricao']
    date_hierarchy = 'data'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'turma', 'turma__curso', 'responsavel_registro'
        ).prefetch_related('estudantes')

"""
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=ocorrencias_ifb
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@ifb.edu.br
EMAIL_HOST_PASSWORD=your-password

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
"""

"""
# ocorrencias_ifb/my_celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')

app = Celery('ocorrencias_ifb')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
"""