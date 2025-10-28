from django.contrib import admin
from .models import Atendimento, TipoAtendimento, SituacaoAtendimento

@admin.register(TipoAtendimento)
class TipoAtendimentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo']

@admin.register(SituacaoAtendimento)
class SituacaoAtendimentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cor', 'ativo']

@admin.register(Atendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display = ['id', 'coordenacao', 'data', 'hora', 'servidor_responsavel', 'tipo_atendimento']
    list_filter = ['coordenacao', 'tipo_atendimento', 'situacao', 'data']
    filter_horizontal = ['estudantes', 'servidores_participantes']