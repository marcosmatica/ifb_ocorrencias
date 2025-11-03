# atendimentos/forms.py

from django import forms
from .models import Atendimento, TipoAtendimento, SituacaoAtendimento
from core.models import Estudante, Servidor, Turma


class AtendimentoForm(forms.ModelForm):
    # Campos de busca para estudantes (não salvos)
    busca_estudante = forms.CharField(
        required=False,
        label="Buscar estudante",
        widget=forms.TextInput(attrs={
            'placeholder': 'Digite o nome ou matrícula do estudante...',
            'class': 'form-control',
            'id': 'busca-estudante'
        })
    )

    # Campo de filtro por turma para estudantes
    turma_filtro = forms.ModelChoiceField(
        queryset=Turma.objects.all().distinct(),
        required=False,
        label="Filtrar estudantes por turma",
        empty_label="Todas as turmas",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'turma-filtro'
        })
    )

    # Campo de busca para servidores
    busca_servidor = forms.CharField(
        required=False,
        label="Buscar servidor",
        widget=forms.TextInput(attrs={
            'placeholder': 'Digite o nome do servidor...',
            'class': 'form-control',
            'id': 'busca-servidor'
        })
    )

    class Meta:
        model = Atendimento
        fields = [
            'coordenacao', 'estudantes', 'data', 'hora',
            'tipo_atendimento', 'situacao', 'origem',
            'informacoes', 'observacoes', 'anexos',
            'servidores_participantes', 'publicar_ficha_aluno'
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hora': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'informacoes': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'estudantes': forms.CheckboxSelectMultiple(attrs={'class': 'estudante-checkbox'}),
            'servidores_participantes': forms.CheckboxSelectMultiple(attrs={'class': 'servidor-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        self.servidor = kwargs.pop('servidor', None)
        super().__init__(*args, **kwargs)

        # Pré-preencher coordenação do servidor
        if self.servidor:
            self.fields['coordenacao'].initial = self.servidor.coordenacao

        # Ordenar estudantes e servidores
        self.fields['estudantes'].queryset = Estudante.objects.all().order_by('nome')
        self.fields['servidores_participantes'].queryset = Servidor.objects.all().order_by('nome')