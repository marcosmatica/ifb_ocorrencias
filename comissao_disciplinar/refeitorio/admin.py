from django.contrib import admin
from .models import ConfigRefeitorio, RegistroRefeicao, BloqueioAcesso

@admin.register(ConfigRefeitorio)
class ConfigRefeitorioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'horario_inicio', 'horario_fim', 'ativo']
    list_filter = ['ativo']

@admin.register(RegistroRefeicao)
class RegistroRefeicaoAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'tipo_refeicao', 'data_hora', 'ip_acesso']
    list_filter = ['tipo_refeicao', 'data_hora']
    search_fields = ['estudante__nome', 'servidor__nome', 'codigo_barras_usado']
    date_hierarchy = 'data_hora'

@admin.register(BloqueioAcesso)
class BloqueioAcessoAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'data_inicio', 'data_fim', 'ativo']
    list_filter = ['ativo', 'data_inicio']