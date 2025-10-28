# atendimentos/forms.py

from django import forms
from .models import Atendimento, TipoAtendimento, SituacaoAtendimento
from core.models import Estudante, Servidor


class AtendimentoForm(forms.ModelForm):
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
            'estudantes': forms.CheckboxSelectMultiple(),
            'servidores_participantes': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        self.servidor = kwargs.pop('servidor', None)
        super().__init__(*args, **kwargs)

        # Pré-preencher coordenação do servidor
        if self.servidor:
            self.fields['coordenacao'].initial = self.servidor.coordenacao