# pedagogico/forms.py

from django import forms
from .models import Disciplina, DisciplinaTurma, ConselhoClasse, InformacaoEstudanteConselho

class DisciplinaForm(forms.ModelForm):
    class Meta:
        model = Disciplina
        fields = ['nome', 'codigo', 'curso', 'carga_horaria', 'ementa', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'curso': forms.Select(attrs={'class': 'form-control'}),
            'carga_horaria': forms.NumberInput(attrs={'class': 'form-control'}),
            'ementa': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ConselhoClasseForm(forms.ModelForm):
    class Meta:
        model = ConselhoClasse
        fields = [
            'turma', 'periodo', 'data_realizacao',
            'informacoes_gerais', 'pontos_positivos', 'pontos_atencao', 'encaminhamentos',
            'coordenacao_curso', 'coordenacao_pedagogica', 'docentes_participantes'
        ]
        widgets = {
            'data_realizacao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'informacoes_gerais': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'pontos_positivos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'pontos_atencao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'encaminhamentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'docentes_participantes': forms.CheckboxSelectMultiple(),
        }

class InformacaoEstudanteConselhoForm(forms.ModelForm):
    class Meta:
        model = InformacaoEstudanteConselho
        fields = [
            'observacoes_gerais', 'frequencia', 'situacao_geral',
            'participacao', 'relacionamento', 'dificuldades', 'potencialidades',
            'necessita_acompanhamento', 'encaminhamento_cdpd', 'encaminhamento_cdae',
            'encaminhamento_napne', 'observacoes_encaminhamento'
        ]
        widgets = {
            'observacoes_gerais': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'participacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'relacionamento': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'dificuldades': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'potencialidades': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observacoes_encaminhamento': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }