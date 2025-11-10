# pedagogico/forms.py

from django import forms
from .models import (
    Disciplina, DisciplinaTurma, ConselhoClasse,
    InformacaoEstudanteConselho, ObservacaoDocenteEstudante,
    ObservacaoDocenteTurma
)
from core.models import Turma, Estudante


class DisciplinaForm(forms.ModelForm):
    class Meta:
        model = Disciplina
        fields = ['nome', 'codigo', 'curso', 'carga_horaria', 'ementa', 'bimestres_ativos', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'curso': forms.Select(attrs={'class': 'form-control'}),
            'carga_horaria': forms.NumberInput(attrs={'class': 'form-control'}),
            'ementa': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'bimestres_ativos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1,2,3,4'
            }),
        }


class ConselhoClasseForm(forms.ModelForm):
    class Meta:
        model = ConselhoClasse
        fields = [
            'turma', 'periodo', 'data_realizacao',
            'perfil_turma', 'informacoes_gerais',
            'pontos_positivos', 'pontos_atencao', 'encaminhamentos',
            'coordenacao_curso', 'coordenacao_pedagogica'
        ]
        widgets = {
            'turma': forms.Select(attrs={'class': 'form-control'}),
            'periodo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2024.1'
            }),
            'data_realizacao': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'perfil_turma': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrição geral do perfil da turma...'
            }),
            'informacoes_gerais': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'pontos_positivos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'pontos_atencao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'encaminhamentos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'coordenacao_curso': forms.Select(attrs={'class': 'form-control'}),
            'coordenacao_pedagogica': forms.Select(attrs={'class': 'form-control'}),
        }


class InformacaoEstudanteConselhoForm(forms.ModelForm):
    """Formulário para coordenação editar informações do estudante"""

    class Meta:
        model = InformacaoEstudanteConselho
        fields = [
            'observacoes_gerais', 'frequencia', 'situacao_geral',
            'participacao', 'relacionamento', 'dificuldades', 'potencialidades',
            'necessita_acompanhamento', 'encaminhamento_cdpd',
            'encaminhamento_cdae', 'encaminhamento_napne',
            'observacoes_encaminhamento'
        ]
        widgets = {
            'observacoes_gerais': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'frequencia': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'situacao_geral': forms.TextInput(attrs={'class': 'form-control'}),
            'participacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'relacionamento': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'dificuldades': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'potencialidades': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observacoes_encaminhamento': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }


class ObservacaoDocenteEstudanteForm(forms.ModelForm):
    """Formulário para docente preencher observação do estudante"""

    class Meta:
        model = ObservacaoDocenteEstudante
        fields = ['observacao', 'observacao_napne']
        widgets = {
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Elogios, encaminhamentos, observações quanto às formas de aprender e ser do estudante...',
                'required': True
            }),
            'observacao_napne': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Informe as adaptações curriculares realizadas para este estudante...'
            }),
        }

    def __init__(self, *args, **kwargs):
        eh_napne = kwargs.pop('eh_napne', False)
        super().__init__(*args, **kwargs)

        if not eh_napne:
            # Remove campo NAPNE se não for necessário
            self.fields.pop('observacao_napne', None)
        else:
            # Torna obrigatório se for NAPNE
            self.fields['observacao_napne'].required = True


class ObservacaoDocenteTurmaForm(forms.ModelForm):
    """Formulário para docente preencher observação da turma"""

    class Meta:
        model = ObservacaoDocenteTurma
        fields = ['observacao']
        widgets = {
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Faça uma descrição da turma conforme sua experiência atual com ela...',
                'required': True
            }),
        }


class DisciplinaTurmaForm(forms.ModelForm):
    """Formulário para assumir/atribuir docente a disciplina"""

    class Meta:
        model = DisciplinaTurma
        fields = ['docente']
        widgets = {
            'docente': forms.Select(attrs={'class': 'form-control'}),
        }