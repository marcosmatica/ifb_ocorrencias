from django.contrib import admin
from .models import (
    FichaEstudanteNAPNE, TipoAtendimentoNAPNE, NecessidadeEspecifica,
    SetorEncaminhamento, StatusAtendimentoNAPNE, AtendimentoNAPNE,
    ObservacaoEncaminhamento
)

@admin.register(FichaEstudanteNAPNE)
class FichaEstudanteNAPNEAdmin(admin.ModelAdmin):
    list_display = ['estudante', 'turma', 'atendido_por', 'laudo_apresentado']
    list_filter = ['laudo_apresentado', 'turma']
    search_fields = ['estudante__nome', 'estudante__matricula_sga']

@admin.register(TipoAtendimentoNAPNE)
class TipoAtendimentoNAPNEAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo']
    list_filter = ['ativo']

@admin.register(NecessidadeEspecifica)
class NecessidadeEspecificaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo']
    list_filter = ['ativo']

@admin.register(SetorEncaminhamento)
class SetorEncaminhamentoAdmin(admin.ModelAdmin):
    list_display = ['sigla', 'nome', 'ativo']
    list_filter = ['ativo']

@admin.register(StatusAtendimentoNAPNE)
class StatusAtendimentoNAPNEAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cor', 'ativo']
    list_filter = ['ativo']

class ObservacaoEncaminhamentoInline(admin.TabularInline):
    model = ObservacaoEncaminhamento
    extra = 1

@admin.register(AtendimentoNAPNE)
class AtendimentoNAPNEAdmin(admin.ModelAdmin):
    list_display = ['id', 'estudante', 'data', 'atendido_por', 'tipo_atendimento', 'status']
    list_filter = ['status', 'tipo_atendimento', 'origem', 'data']
    search_fields = ['estudante__nome', 'estudante__matricula_sga']
    filter_horizontal = ['necessidades_especificas']
    inlines = [ObservacaoEncaminhamentoInline]
    date_hierarchy = 'data'