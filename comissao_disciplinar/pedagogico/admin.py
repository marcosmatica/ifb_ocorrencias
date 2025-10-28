from django.contrib import admin
from .models import Disciplina, DisciplinaTurma, ConselhoClasse, InformacaoEstudanteConselho, FichaAluno

@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'curso', 'carga_horaria', 'ativa']
    list_filter = ['curso', 'ativa']

@admin.register(DisciplinaTurma)
class DisciplinaTurmaAdmin(admin.ModelAdmin):
    list_display = ['disciplina', 'turma', 'docente', 'periodo']
    list_filter = ['periodo', 'turma']

@admin.register(ConselhoClasse)
class ConselhoClasseAdmin(admin.ModelAdmin):
    list_display = ['turma', 'periodo', 'data_realizacao', 'coordenacao_curso']
    list_filter = ['periodo', 'turma__curso']
    filter_horizontal = ['docentes_participantes']

@admin.register(InformacaoEstudanteConselho)
class InformacaoEstudanteConselhoAdmin(admin.ModelAdmin):
    list_display = ['conselho', 'estudante', 'necessita_acompanhamento']
    list_filter = ['necessita_acompanhamento', 'encaminhamento_cdpd', 'encaminhamento_cdae']

@admin.register(FichaAluno)
class FichaAlunoAdmin(admin.ModelAdmin):
    list_display = ['estudante', 'ultima_atualizacao']
